import sys
import argparse


# argparse setup for calling from command line
parser = argparse.ArgumentParser(description='Convert data to BIDS format')
parser.add_argument('origpath', type=str, )
