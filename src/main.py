'''
Reference implementation of node2vec. 

Author: Aditya Grover

For more details, refer to the paper:
node2vec: Scalable Feature Learning for Networks
Aditya Grover and Jure Leskovec 
Knowledge Discovery and Data Mining (KDD), 2016
'''

import argparse
import numpy as np
import networkx as nx
import node2vec
from gensim.models import Word2Vec

import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

from numba import jit


def parse_args():
    '''
    Parses the node2vec arguments.
    '''
    parser = argparse.ArgumentParser(description="Run node2vec.")

    parser.add_argument('--input', nargs='?', default='graph/karate.edgelist',
                        help='Input graph path')

    parser.add_argument('--output', nargs='?', default='emb/karate.emb',
                        help='Embeddings path')

    parser.add_argument('--dimensions', type=int, default=128,
                        help='Number of dimensions. Default is 128.')

    parser.add_argument('--walk-length', type=int, default=80,
                        help='Length of walk per source. Default is 80.')

    parser.add_argument('--num-walks', type=int, default=10,
                        help='Number of walks per source. Default is 10.')

    parser.add_argument('--window-size', type=int, default=10,
                        help='Context size for optimization. Default is 10.')

    parser.add_argument('--iter', default=1, type=int,
                        help='Number of epochs in SGD')

    parser.add_argument('--workers', type=int, default=8,
                        help='Number of parallel workers. Default is 8.')

    parser.add_argument('--p', type=float, default=1,
                        help='Return hyperparameter. Default is 1.')

    parser.add_argument('--q', type=float, default=1,
                        help='Inout hyperparameter. Default is 1.')

    parser.add_argument('--weighted', dest='weighted', action='store_true',
                        help='Boolean specifying (un)weighted. Default is unweighted.')
    parser.add_argument('--unweighted', dest='unweighted', action='store_false')
    parser.set_defaults(weighted=False)

    parser.add_argument('--directed', dest='directed', action='store_true',
                        help='Graph is (un)directed. Default is undirected.')
    parser.add_argument('--undirected', dest='undirected', action='store_false')
    parser.add_argument('--multiprocess', dest='multiprocess', action='store_true',
                        help='Boolean specifying if multiprocessing mode should be use.')
    parser.set_defaults(multiprocess=False)
    parser.set_defaults(directed=False)

    return parser.parse_args()


def read_graph():
    '''
    Reads the input network in networkx.
    '''

    if args.input.endswith('.gml'):
        G = nx.read_gml(args.input)
        if not args.weighted:
            for edge in G.edges():
                G[edge[0]][edge[1]]['weight'] = 1
    else:
        if args.weighted:
            G = nx.read_edgelist(args.input, nodetype=int, data=(('weight', float),), create_using=nx.DiGraph())
        else:
            G = nx.read_edgelist(args.input, nodetype=int, create_using=nx.DiGraph())
            for edge in G.edges():
                G[edge[0]][edge[1]]['weight'] = 1

    if not args.directed:
        G = G.to_undirected()

    return G


def learn_embeddings(walks, G):
    '''
    Learn embeddings by optimizing the Skipgram objective using SGD.
    '''
    walks = [map(lambda u: str(G.G.degree(u)), walk) for walk in walks]
    model = Word2Vec(walks, size=args.dimensions, window=args.window_size, min_count=0, sg=1, workers=args.workers,
                     iter=args.iter)
    model.wv.save_word2vec_format(args.output)

    return model


@jit
def main(args):
    '''
    Pipeline for representational learning for all nodes in a graph.
    '''
    nx_G = read_graph()
    G = node2vec.Graph(nx_G, args.directed, args.p, args.q)
    if args.multiprocess:
        G.preprocess_transition_probs_multi()
        walks = G.simulate_walks_mult(args.num_walks, args.walk_length)
    else:
        G.preprocess_transition_probs()
        walks = G.simulate_walks(args.num_walks, args.walk_length)
    model = learn_embeddings(walks, G)
    vec = [model.wv.get_vector(str(G.G.degree(node))) for node in nx_G.nodes().keys()]
    random_state = 170
    y_prediction = KMeans(n_clusters=3, random_state=random_state).fit_predict(vec)
    nx.draw(nx_G, pos=nx.kamada_kawai_layout(nx_G), node_color=y_prediction, edge_color='gray')

    plt.show()
    return


if __name__ == "__main__":
    args = parse_args()
    main(args)
