"""
Turn the original data into the corresponding graphs and the corresponding annotations
"""

import sys
import os

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.join(script_dir, '..'))

from data_processor.chopper import all_rna_process
from data_processor.annotator import annotate_all
from tools.utils import makedir


def setup_dirs():
    """
    Adds all ignored features
    :return:
    """
    script_dir = os.path.dirname(__file__)
    makedir(os.path.join(script_dir, '../data/annotated'), permissive=True)
    makedir(os.path.join(script_dir, '../data/graphs'), permissive=True)
    print('Done creating files')


def preprocess_data(name, in_graph='samples_graphs', in_pdb='samples_pdb'):
    """

    :param name: name of the 'experiment' : where the data is going to be produced
    :param in_graph: name of the folder of the data to read from
    :param in_pdb: name of the folder of the pdb to read from
    :return:
    """
    script_dir = os.path.dirname(__file__)
    graph_path = os.path.join(script_dir, "../data/graphs/", name)
    annotated_path = os.path.join(script_dir, "../data/annotated/", name)
    makedir(graph_path, permissive=False)
    makedir(annotated_path, permissive=False)
    all_rna_process(graph_path='../data/' + in_graph, pdb_path='../data/' + in_pdb, dest=graph_path)
    print('Done producing graphs')

    annotate_all(graph_path=graph_path, dump_path=annotated_path)
    print('Done annotating graphs')

    print('Done producing data')


if __name__ == '__main__':
    setup_dirs()

    in_graph = 'carnaval'
    in_pdb = 'all_rna_pdb'
    name = 'whole'
    preprocess_data(in_graph=in_graph, in_pdb=in_pdb, name=name)
