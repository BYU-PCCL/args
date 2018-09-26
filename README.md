	  
	import torch
	import torch.nn as nn

	class SubDataset:
	  def __init__(self, root='/', optimizer:argchoice=[torch.optim.Adam, torch.optim.SGD]):
	    pass
	  
	class Networkblock:
	  def __init__(self, root='/', age:int=1, dictionary={'name': 'robert'}, sad:int=None, l=[1.0, 2], test:argchoice=[torch.nn, torch.optim], module:argchoice=[torch.nn.CrossEntropyLoss, torch.nn], subdataset:argchoice=[SubDataset]):
	    subdataset()
	    
	    
	class DatasetTwo:
	  def __init__(self, root='/', other=True):
	    subdataset()
	    
	    
	class Model:
	  def __init__(self, num_layers=5, activation_fn:argchoice=[Networkblock]):
	    #if has_residual:
	    
	    from all_models import *
	    
	module('dataset', [DatasetTwo])
	module('optimizer', torch.optim)
	module('model', all_models)
	arguments(epochs=1.0, resume=True)
	arguments('dothing', default=True)
	arguments('-i', default=True)
	defaults({'dataset.subdataset.optimizer.lr': 1e-8})

	args = reader()

	#todo: test dictionary
	#todo: test argignore
	#todo: test arggroup
	#todo: allow functions in addition to modules and classes

	# print(args)
	# print(args.dataset)
	# print(args.epochs)
	# print(args['dataset.age'])
	# print(ds == args.dataset)

	# print('is default?', args.isdefault('dataset'))
	# print('is default?', args.isdefault('dataset.l'))
	# print('is default?', args.isdefault('dataset.sad'))
	# print('is default?', args.isdefault('epochs'))

	# print(args.dothing)
	# print(args['dataset.dictionary'])

	_parser.print_help()

	print(args.optimizer)

	#--model.activation_fn ELU --model.activation_fn.alpha 