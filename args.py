import argparse
import sys
import inspect
from collections import defaultdict, Iterable
import json
import os
import colorama
import textwrap
import pickle
import hashlib

_parser = argparse.ArgumentParser(prog= '',
                                  add_help=True, 
                                  formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=50, width=100))
_defaults = {}
_reconstructed_arguments = {}
_helpless_args = [a for a in sys.argv if a != '-h' and a != '--help']

def _flatten(input):
    new_list = []
    if isinstance(input, Iterable):
      for i in input:
        new_list += _flatten(i)
      return new_list
    else:
      return [input]

class DictAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
      parsed_class = self.choices.get(values, self.default)
      setattr(namespace, self.dest, parsed_class)

def argignore(cls):
  class _Wrapper(object):
    def __init__(self, *args, **kwargs):
      cls.__argignore__ = True

  return _Wrapper

# def arggroup(cls, group_name):
#   class Wrapper(object):
#     def __init__(self, *args, **kwargs):
#       cls.__arggroup__ = group_name
#   return Wrapper

class argchoice(object):
  def __init__(self, *args):
    print(args[0])
    self.choices = _flatten(args)
    
  def __getitem__(self, i):
    return self.choices[i]
  
  def __repr__(self):
    return '{}({})'.format(self.__class__.__name__, ', '.join([c.__name__ for c in self.choices]))

# enables a user to specify a parent class, and choose from all decendent classes
class argsubclass(argchoice):
  def __init__(self, *args):
    choices = [argsubclass.subclasses(a) for a in args]
    super(argmodule, self).__init__(choices)
    
  @staticmethod
  def subclasses(cls):
    all_subclasses = []

    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(argsubclass.subclasses(subclass))

    return all_subclasses

# centralize the adding of an argument
def _arg(arg_name, *args, **kwargs):
  assert 'default' in kwargs or 'type' in kwargs, 'please specify a default or a type for argument {}'.format(arg_name)
  
  kwargs['type'] = type(kwargs['default']) if 'default' in kwargs else kwargs['type']
  
  if 'metavar' not in kwargs:
    kwargs['metavar'] = kwargs['type'].__name__
    
  if 'help' not in kwargs:
    kwargs['help'] = kwargs['type'].__name__ + ' default: %(default)s'
    
  if '._' in arg_name or arg_name[0] == '_':
      kwargs['help'] = argparse.SUPPRESS

  if kwargs['type'] == bool:
    # https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    def strbool(v):
      if v.lower() in ('yes', 'true', 't', 'y', '1'):
          return True
      elif v.lower() in ('no', 'false', 'f', 'n', '0'):
          return False
      else:
          raise argparse.ArgumentTypeError('Boolean value expected.')
          
    kwargs['type'] = strbool
    
  prefix = '--' if arg_name[0] != '-' else ''
  _parser.add_argument(prefix + arg_name, *args, **kwargs)

def module(arg_name, class_list, **kwargs):
  class_list = [class_list] if not hasattr(class_list, '__iter__') else class_list
  
  assert len(class_list) > 0, '{} cannot be an empty list'.format(arg_name)
  
  # convert modules into classes
  filtered_classes = []
  for m in class_list:
    if inspect.ismodule(m):
      # add the classes that are direct submodules of the requested module
      all_classes = [getattr(m, x) for x in dir(m) if inspect.isclass(getattr(m, x)) and getattr(m, x).__module__ == m.__name__]
      filtered_classes += [c for c in all_classes if not hasattr(c, '__argignore__')]
  class_list += filtered_classes
  
  # remove the modules from the list
  class_list[:] = [c for c in class_list if inspect.isclass(c) and c.__name__[0] != '_']
  
  # add the argument which decides the class
  _parser.add_argument('--' + arg_name,
                      default=kwargs['default'] if 'default' in kwargs else class_list[0], 
                      metavar='class', 
                      help='{%(choices)s} (default: %(default)s)' if len(class_list) > 1 else argparse.SUPPRESS, 
                      choices={o.__name__:o for o in class_list}, 
                      action=DictAction)
   
  # see if the user has specified this argument to determine what additional
  # argument we should add
  parsed_class = vars(_parser.parse_known_args(_helpless_args)[0])[arg_name]
  
  # create aligned dictionaries with the default type parameters (annotations)
  sig = inspect.getfullargspec(parsed_class.__init__)
  sigdefaults = sig.defaults or []
  sigdefaults = defaultdict(lambda: None, dict(zip(sig.args[::-1], sigdefaults[::-1])))
  sigtypes = {arg:type(sigdefaults[arg]) for arg in sig.args}
  sigtypes.update(sig.annotations)
  
  # loop through the __init__ signiture and add arguments
  for arg in sig.args:
    param_name = '{}.{}'.format(arg_name, arg)

    # if the argument is a class or module, recurse
    if issubclass(sigtypes[arg], argchoice):
      module(arg_name + '.' + arg, sigdefaults[arg], **kwargs)
    
    # if the argument is a normal parameter (a leaf)
    else:
      param_name = '{}.{}'.format(arg_name, arg)
      helpstring = parsed_class.__name__ + ' default: %(default)s'
      nargs = None
      t = sigtypes[arg]
      metavar = sigtypes[arg].__name__

      # handle unsual types which are not processed by argparse properly
      if sigtypes[arg] is list:
        t = type(sigdefaults[arg][0])
        nargs = '+'
      elif sigtypes[arg] is tuple:
        t = type(sigdefaults[arg][0])
        nargs = len(sigdefaults[arg])  
      elif sigtypes[arg] is dict:
        t = json.loads 
      elif sigtypes[arg] is type(None):
        continue

      arguments(param_name,
             default=sigdefaults[arg], 
             metavar=metavar, 
             help=helpstring,
             nargs=nargs,
             type=t)

  # construct a holding class which when called will return an initialized
  # version of parsed_class using any arguments passed in at the command line
  class Recon(object):
    __reconstructed_class__ = parsed_class
      
    def __repr__(self):
      return '<ArgProcessed {}>'.format(str(parsed_class))
    
    def __call__(self, *args, **kwargs):
      defaults()
      recon_defaults = {}
      parsed_args = vars(_parser.parse_known_args(_helpless_args)[0])
      for k, v in parsed_args.items():
        parameter = k[len(arg_name + '.'):]
        if k.startswith(arg_name + '.') and len(parameter.split('.')) == 1:
          recon_defaults[parameter] = _reconstructed_arguments[k] if k in _reconstructed_arguments else v
      
      # prefer the arguments specified at initialization time
      recon_defaults.update(kwargs)
      
      return parsed_class(*args, **recon_defaults)

  # keep a running list of these reconstructed classes
  # you might think "can't we do this inside DictAction?" but argparse doesn't
  # run the action on default arguments
  _reconstructed_arguments[arg_name] = Recon()
  
  return _reconstructed_arguments[arg_name]

def arguments(*args, **kwargs):
  if len(args) == 0:
    for arg_name, default in kwargs.items():
      _arg(arg_name, default=default)
  else:
    _arg(*args, **kwargs)

def defaults(d=None):
  d = _defaults if d is None else d
  for arg in d:
    tup = _parser._parse_optional('--' + arg)
    if tup is not None and tup[0] is not None:
      tup[0].default = d[arg]
  _defaults.update(d)

class reader():
  def __init__(self, ):
    defaults()
    self.parsed_args = vars(_parser.parse_args())
    self.parsed_args.update(_reconstructed_arguments)
    self.default_arguments = {a.option_strings[0][2:]: a.default for a in _parser._actions}

  def __getitem__(self, item):
    return self.parsed_args[item]
    
  def __getattr__(self, item):
    return self.parsed_args[item]
    
  def __repr__(self):
    string = []
    for a in self.parsed_args:
      s, color = '', ''
      t = type(self.parsed_args[a]).__name__
      if t == 'Recon':
        t = ''
      if not self.isdefault(a):
        s, color = '*', colorama.Fore.GREEN + colorama.Style.BRIGHT
      line = '{}{:>30}{:<1} : {} {}{}{}'.format(color, a, s, str(self.parsed_args[a]), colorama.Style.DIM, t, colorama.Style.RESET_ALL)
      string.append(textwrap.fill(line, 90, subsequent_indent=' ' * 34))

    return '\n'.join(string)
  
  def __iter__(self):
    return iter(self.parsed_args)

  def stub(self):
    stub = []
    for arg in self.parsed_args:
      if not self.isdefault(arg):
        stub += ['{}={}'.format(arg, repr(self.parsed_args[arg]) if type(self.parsed_args[arg]) != str else self.parsed_args[arg])]
    return '-'.join(stub)
  
  def command(self):
    return ' '.join(sys.argv)

  def isdefault(self, arg):
    if arg in _reconstructed_arguments:
      return self.parsed_args[arg].__reconstructed_class__.__name__ == self.default_arguments[arg].__name__
    return self.default_arguments[arg] == self.parsed_args[arg]

def parser():
  return _parser