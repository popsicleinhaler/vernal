"""
File to use and expand the meta graph
"""

import sys
import os
import pickle
import json
import matplotlib.pyplot as plt
import time
import numpy as np
import random

script_dir = os.path.dirname(os.path.realpath(__file__))
if __name__ == "__main__":
    sys.path.append(os.path.join(script_dir, '..'))

from tools.graph_utils import whole_graph_from_node, has_NC, induced_edge_filter, bfs_expand
from tools.learning_utils import inference_on_graph_run
from tools.new_drawing import rna_draw, rna_draw_pair, rna_draw_grid
from build_motifs.meta_graph import MGraph, MGraphAll


def parse_json_old(json_file):
    """
    Parse the json motifs to only get the ones with examples in our data
    and return a dict {motif_id : list of list of nodes (instances)}
    """

    def parse_dict(dict_to_parse, motifs_prefix):
        """
        inner function to apply to bgsu and carnaval dicts
        """
        res_dict = dict()
        for motif_id, motif_instances in dict_to_parse.items():
            filtered_instances = list()
            for instance in motif_instances:
                filtered_instance = []
                for node in instance:
                    node = node['node']
                    if node is not None:
                        (a, (b, c)) = node
                        node = (a, (b, c))
                        filtered_instance.append(node)
                if filtered_instance:
                    filtered_instances.append(filtered_instance)
            if filtered_instances:
                motif_id = (motifs_prefix, motif_id)
                res_dict[motif_id] = filtered_instances
        return res_dict

    whole_dict = json.load(open(json_file, 'r'))

    motifs = dict()

    rna3dmotif = parse_dict(whole_dict['rna3dmotif'], 'rna3dmotif')
    motifs.update(rna3dmotif)

    # bgsu = parse_dict(whole_dict['bgsu'], 'bgsu')
    # motifs.update(bgsu)
    #
    # carnaval = parse_dict(whole_dict['carnaval'], 'carnaval')
    # motifs.update(carnaval)
    return motifs


def parse_json_new(json_file):
    """
    Same as above with the new motifs nomenclature

    The json contains a dict :
    {

    """

    def parse_dict(dict_to_parse, motifs_prefix):
        """
        inner function to apply to bgsu and carnaval dicts
        """
        res_dict = dict()
        counter_none = 0
        counter_not_none = 0
        for motif_id, motif_instances in dict_to_parse.items():
            filtered_instances = list()
            for instance in motif_instances:
                filtered_instance = []
                for node in instance:
                    node = node['node']
                    if node is not None:
                        # (a, (b, c)) = node
                        # node = (a, (b, c))
                        counter_not_none += 1
                        filtered_instance.append(node)
                    else:
                        counter_none += 1
                if filtered_instance:
                    filtered_instances.append(filtered_instance)
            if filtered_instances:
                motif_id = (motifs_prefix, motif_id)
                res_dict[motif_id] = filtered_instances
        # print(counter_none)
        # print(counter_not_none)
        return res_dict

    whole_dict = json.load(open(json_file, 'r'))
    motifs = dict()

    # json_graph = load_json('../data/1njp.json')
    # node_id = '1njp.0.1797'
    # print(node_id in json_graph.nodes())

    rna3dmotif = parse_dict(whole_dict['rna3dmotif'], 'rna3dmotif')
    motifs.update(rna3dmotif)

    bgsu = parse_dict(whole_dict['bgsu'], 'bgsu')
    motifs.update(bgsu)

    carnaval = parse_dict(whole_dict['carnaval'], 'carnaval')
    motifs.update(carnaval)
    return motifs


def prune_motifs(motifs_dict, shortest=4, sparsest=3, non_canonical=True, non_redundant=True,
                 graph_dir=os.path.join(script_dir, '../data/graphs/NR'),
                 non_redundant_dir=os.path.join(script_dir, '../data/graphs/NR')):
    """
    Clean the dict by removing sparse or small motifs
    :param motifs_dict:
    :return:
    """
    res_dict = {}
    sparse, short, nc = 0, 0, 0
    tot_inst, nr_inst = 0, 0
    mean_instance, mean_nodes = list(), list()

    non_redundant_list = set(os.listdir(non_redundant_dir))

    for motif_id, instances in motifs_dict.items():
        instance = instances[0]
        if non_redundant:
            tot_inst += len(instances)
            instances = [instance for instance in instances if f"{instance[0][:4]}.json" in non_redundant_list]
            nr_inst += len(instances)
        if len(instances) < sparsest:
            sparse += 1
            continue
        if len(instance) < shortest:
            short += 1
            continue
        if non_canonical:
            graph = whole_graph_from_node(instance[0], graph_dir=graph_dir)
            motif_graph = graph.subgraph(instance)
            if not has_NC(motif_graph, label='LW'):
                nc += 1
                continue
        mean_instance.append(len(instances))
        mean_nodes.append(len(instances[0]))
        res_dict[motif_id] = instances

    print(f'filtered {sparse} on sparsity, {short} on length, {nc} on non canonicals')
    print(f'non redundancy removed {tot_inst - nr_inst} /{tot_inst} instances')
    print(f'On average, {np.mean(mean_instance)} instances of motifs with {np.mean(mean_nodes)} nodes')
    return res_dict


def old_to_new_nodes(old_id):
    """
        Go from ('{pdb}.nx', ('{chain}', int resid)) -> '{pdb}.{chain}.{resid}'

    """
    pdbnx, (chain, resid) = old_id
    pdb = pdbnx[:-3]
    new_id = f'{pdb}.{chain}.{resid}'


def old_to_new_motifs(motif_idlist):
    """
        rename motifs dicts
    """
    new_motif_idlist = list()
    for old_id in motif_idlist:
        new_id = old_to_new_nodes(old_id)
        new_motif_idlist.append(new_id)
    return new_motif_idlist


def compute_embs(instance, run):
    """
    :param instance: a list of nodes that form a motif
    Parse the json motifs to only get the ones with examples in our data
    and return a dict {motif_id : list of list of nodes (instances)}
    """
    source_graph = whole_graph_from_node(instance[0])
    embs, node_map = inference_on_graph_run(run, source_graph)
    return embs, node_map


def get_outer_border(nodes, graph=None):
    if graph is None:
        graph = whole_graph_from_node(nodes[0])
    # expand the trimmed retrieval
    out_border = set()
    for node in nodes:
        for nei in graph.neighbors(node):
            if nei not in nodes:
                out_border.add(nei)
    return out_border


def trim(instance, depth=1, whole_graph=None):
    """
    Remove nodes around the border of a motif
    """
    if whole_graph is None:
        whole_graph = whole_graph_from_node(instance[0])
    out_border = get_outer_border(instance, whole_graph)
    # get the last depth ones as well as the cumulative set
    cummulative, last = out_border, out_border
    for d in range(depth):
        depth_ring = set()
        for node in last:
            for nei in whole_graph.neighbors(node):
                if nei not in cummulative:
                    depth_ring.add(nei)
        last = depth_ring
        cummulative = cummulative.union(depth_ring)
    trimmed_instance = [node for node in instance if node not in cummulative]
    return trimmed_instance


def trim_try(whole_graph, instance, depth=1):
    """
    To keep some graph, we cannot always perform trimming. Try with decreasing values of depth
    :param graph:
    :param instance:
    :param max_depth:
    :return:
    """
    trimmed = []
    trimmed_graph = whole_graph.subgraph(trimmed)
    # Start with empty graph.
    # Then the successive graphs are supposedly bigger up until they are not empty
    while not trimmed_graph.edges():
        if depth < 1:
            trimmed = instance
            trimmed_graph = whole_graph.subgraph(instance)
            return trimmed, trimmed_graph, depth
        trimmed = trim(instance, depth=depth, whole_graph=whole_graph)
        trimmed_graph = whole_graph.subgraph(trimmed)
        # print('total edges : ', len(trimmed_graph.edges()))
        # print('depth : ', depth)
        depth -= 1
    return trimmed, trimmed_graph, depth + 1


def plot_instance(instance, source_graph=None):
    """
    Plot an extended, native, and trimmed motif.
    :param instance:
    :return:
    """
    if source_graph is None:
        source_graph = whole_graph_from_node(instance[0])
    trimmed = trim(instance)
    out_border = get_outer_border(instance, source_graph)
    extended = instance + list(out_border)
    g_motif = source_graph.subgraph(extended)
    rna_draw(g_motif, node_colors=['red' if n in trimmed else 'blue' if n in instance else 'grey' for n in
                                   g_motif.nodes()])
    plt.show()


def draw_hit(hit, mg, instance=None):
    """
    Plot the hit. If an instance is given, then compares this hit with the original instance
    :param hit:
    :param mg:
    :param instance:
    :param compare:
    :return:
    """
    try:
        hit_graph = whole_graph_from_node(hit[0])
    except:
        hit = [mg.reversed_node_map[i] for i in hit]
        hit_graph = whole_graph_from_node(hit[0])

    out_border = get_outer_border(hit, hit_graph)
    full_hit = hit + list(out_border)
    out_border = get_outer_border(full_hit, hit_graph)
    extended_hit = full_hit + list(out_border)
    g_hit = hit_graph.subgraph(extended_hit)
    if instance is not None:
        source_graph = whole_graph_from_node(instance[0])
        trimmed = trim(instance)
        out_border = get_outer_border(instance, source_graph)
        extended = instance + list(out_border)
        g_motif = source_graph.subgraph(extended)
        rna_draw_pair((g_motif, g_hit)
                      , node_colors=(
                ['red' if n in trimmed else 'blue' if n in instance else 'grey' for n in g_motif.nodes()],
                ['red' if n in hit else 'blue' if n in full_hit else 'grey' for n in g_hit.nodes()]))
        plt.show()
    else:
        rna_draw(g_hit, node_colors=['red' if n in hit else 'blue' if n in full_hit else 'grey' for n in g_hit.nodes()])
        plt.show()


def retrieve_instances(query_instance, mg, depth=1):
    """
    Trim a query motif instance as much as possible to remove border effects,
        then call retrieve with this query graph
    """
    # DEBUG
    # print(query_instance)
    # query_g = whole_graph_from_node(motif[0][0]).subgraph(motif[0])
    # failure_g = whole_graph_from_node(motif[1][0]).subgraph(motif[1])
    # failure_g2 = whole_graph_from_node(motif[2][0]).subgraph(motif[2])
    # rna_draw_pair((query_g, failure_g))
    # plt.show()
    # rna_draw_pair((query_g, failure_g2))
    # plt.show()
    # rna_draw_pair((failure_g2, failure_g))
    # plt.show()

    query_whole_graph = whole_graph_from_node(query_instance[0])

    # Sometimes one can not trim the motif as much as we could have like, so we need to trim less
    trimmed, trimmed_graph, actual_depth = trim_try(query_whole_graph, query_instance, depth=depth)
    start = time.perf_counter()
    retrieved_instances = mg.retrieve_2(trimmed)
    print(f">>> Retrieved {len(retrieved_instances)} instances in {time.perf_counter() - start}")
    return retrieved_instances


def find_hits(motif, mg, depth=1, query_instance=None):
    """
    Use first instance to retrieve others.

    We iterate through the results dict {frozenset of ids : score} and keep the intersection with highest score.
    """
    if query_instance is None:
        query_instance = motif[0]
    retrieved_instances = retrieve_instances(mg=mg, depth=depth, query_instance=query_instance)
    if len(retrieved_instances) == 0:
        return 0, 0, 1, 1

    # start = time.perf_counter()
    sorted_scores = sorted(list(retrieved_instances.values()), key=lambda x: -x)
    res = list()
    failed = 0
    # Now can we find the other instances in our hitlist : iterate through them and keep the best overlap
    for other_instance in motif[1:]:
        instance_res = 0
        # convert motif into set of ids
        try:
            set_form = set([mg.node_map[node] for node in other_instance])

        except KeyError:
            # print(f"one motif instance was missing in the node map : {other_instance}")
            failed += 1
            continue

        best = -1
        for hit, score in retrieved_instances.items():
            if len(hit.intersection(set_form)) > 0:
                if score > best:
                    best = score
                    rank = sorted_scores.index(score)
                    instance_res = (hit, score, rank)

            # DEBUG PLOTS
            # query_g = whole_graph_from_node(motif[0][0]).subgraph(motif[0])
            # failure_g = whole_graph_from_node(other_instance[0]).subgraph(other_instance)
            # rna_draw_pair((query_g, failure_g))
            # plt.show()
            # raise ValueError()
        if instance_res == 0:
            failed += 1
        else:
            res.append(instance_res)

    #
    instance_ranks = [item[2] for item in res]
    if not instance_ranks:
        mean_best = len(retrieved_instances)
    else:
        mean_best = np.mean(instance_ranks)
    best_ratio = mean_best / len(retrieved_instances)
    fail_ratio = failed / len(motif[1:])
    # print(res)
    # print(f">>> Hits parsed in {time.perf_counter() - start}")

    return mean_best, best_ratio, failed, fail_ratio


def hit_ratio_all(motifs, mg, depth=1, max_instances_to_look_for=None):
    # Motif 1 and 2 are isomorphic...
    # motifs = list(motifs.values())[:4]
    # query_g = whole_graph_from_node(motifs[0][0][0]).subgraph(motifs[0][0])
    # failure_g = whole_graph_from_node(motifs[1][0][0]).subgraph(motifs[1][0])
    # rna_draw_pair((query_g, failure_g))
    # plt.show()
    all_best = list()
    all_best_ratio = list()
    all_fails = list()
    all_fails_ratio = list()
    for i, (motif_id, motif) in enumerate(motifs.items()):
        if max_instances_to_look_for is not None and int(i) >= max_instances_to_look_for:
            break
        print()
        print('attempting id : ', motif_id)
        mean_best, best_ratio, failed, fail_ratio = find_hits(motif, mg, depth=depth)
        all_best.append(mean_best)
        all_fails.append(failed)
        all_best_ratio.append(best_ratio)
        all_fails_ratio.append(fail_ratio)
    print(f'on average, {np.mean(all_fails):.4f} fails for a {np.sum(all_fails_ratio):.4f} ratio')
    print(f'And {np.mean(all_best):.4f} rank for a {np.mean(all_best_ratio):.4f} ratio')
    return all_fails, all_best


def ab_testing(motifs, mg, depth=1):
    # Motif 1 and 2 are isomorphic...
    # motifs = list(motifs.values())[:4]
    # query_g = whole_graph_from_node(motifs[0][0][0]).subgraph(motifs[0][0])
    # failure_g = whole_graph_from_node(motifs[1][0][0]).subgraph(motifs[1][0])
    # rna_draw_pair((query_g, failure_g))
    # plt.show()
    all_best = list()
    all_best_ratio = list()
    all_fails = list()
    all_fails_ratio = list()
    other_all_best = list()
    other_all_best_ratio = list()
    other_all_fails = list()
    other_all_fails_ratio = list()
    results_dict = dict()

    all_motifs = [(motif_id, motif) for motif_id, motif in motifs.items()]
    for i, (motif_id, motif) in enumerate(all_motifs):

        # if int(motif_id) != 5:
        #     continue
        print('attempting id : ', motif_id)
        mean_best, best_ratio, failed, fail_ratio = find_hits(motif, mg, depth=depth)
        all_best.append(mean_best)
        all_fails.append(failed)
        all_best_ratio.append(best_ratio)
        all_fails_ratio.append(fail_ratio)

        # Pick another random that is not the current graph
        other_random = random.randint(0, len(all_motifs) - 2)
        if other_random >= i:
            other_random += 1
        random_query_instance = all_motifs[other_random][1][0]

        # Try getting hits for the motif at hands with this random instance
        decoy_mean_best, decoy_best_ratio, decoy_failed, decoy_fail_ratio = \
            find_hits(motif, mg, depth=depth, query_instance=random_query_instance)
        other_all_best.append(decoy_mean_best)
        other_all_fails.append(decoy_failed)
        other_all_best_ratio.append(decoy_best_ratio)
        other_all_fails_ratio.append(decoy_fail_ratio)
        results_dict[motif_id] = (mean_best, best_ratio, failed, fail_ratio, random_query_instance,
                                  decoy_mean_best, decoy_best_ratio, decoy_failed, decoy_fail_ratio)
    print(f'on average, {np.mean(all_fails):.4f} fails for a {np.mean(all_fails_ratio):.4f} ratio')
    print(f'And {np.mean(all_best):.4f} rank for a {np.mean(all_best_ratio):.4f} ratio')
    print(f'For random query, {np.mean(other_all_fails):.4f} fails for a {np.mean(other_all_fails_ratio):.4f} ratio')
    print(f'And {np.mean(other_all_best):.4f} rank for a {np.mean(other_all_best_ratio):.4f} ratio')
    return results_dict


def parse_ab_testing(results_dict):
    all_best = list()
    all_best_ratio = list()
    all_fails = list()
    all_fails_ratio = list()
    other_all_best = list()
    other_all_best_ratio = list()
    other_all_fails = list()
    other_all_fails_ratio = list()

    for motif_id, (mean_best, best_ratio, failed, fail_ratio, random_query_instance, decoy_mean_best, decoy_best_ratio,
                   decoy_failed, decoy_fail_ratio) in results_dict.items():
        if not motif_id[0] == 'carnaval':
            # if not motif_id[0]=='bgsu':
            continue
        # print(f"{motif_id}, "
        #       # f"success rate {1-fail_ratio:1f}, "
        #       # f" decoy success rate {1-decoy_fail_ratio:1f}, "
        #       f"mean rank :{best_ratio:.2f}, "
        #       f"decoy mean rank :{decoy_best_ratio:.2f}, "
        #       f"ratio mean rank :{best_ratio/(decoy_best_ratio+0.001):.3f}"
        #       )
        all_best.append(mean_best)
        all_fails.append(failed)
        all_best_ratio.append(best_ratio)
        all_fails_ratio.append(fail_ratio)
        other_all_best.append(decoy_mean_best)
        other_all_fails.append(decoy_failed)
        other_all_best_ratio.append(decoy_best_ratio)
        other_all_fails_ratio.append(decoy_fail_ratio)

    print(f'on average, {np.mean(all_fails):.4f} fails for a {np.mean(all_fails_ratio):.4f} ratio')
    print(f'And {np.mean(all_best):.4f} rank for a {np.mean(all_best_ratio):.4f} ratio')
    print(f'For random query, {np.mean(other_all_fails):.4f} fails for a {np.mean(other_all_fails_ratio):.4f} ratio')
    print(f'And {np.mean(other_all_best):.4f} rank for a {np.mean(other_all_best_ratio):.4f} ratio')


def match_sizes(graph_to_match, in_graph, whole_in_graph):
    """
    Take the in_graph and trim it up until it is smaller than the 'graph to match'.
    Then expand it to make it a bit bigger
    """
    # print('before anything', in_graph.nodes(), len(in_graph.nodes()))
    # If it's too big, make it smaller, nothing happens if already small
    in_graph_nodes = in_graph.nodes()
    counts = 0
    while len(in_graph_nodes) > len(graph_to_match):
        temp_in_graph_nodes = trim(instance=in_graph_nodes,
                                   depth=1,
                                   whole_graph=whole_in_graph)
        if len(temp_in_graph_nodes) <= 0 or counts > 5:
            break
        else:
            in_graph_nodes = temp_in_graph_nodes
        counts += 1
    in_graph = in_graph.subgraph(in_graph_nodes)
    # print('after making smaller', in_graph.nodes(), len(in_graph.nodes()))
    # If it's too small make the opposite, we do not need to update the depth in the loop as we start
    # from a larger and larger set of nodes.
    # Successive growth is fairer, as the border nodes are not connected with one another
    counts = 0
    while len(in_graph_nodes) < len(graph_to_match):
        in_graph = induced_edge_filter(whole_in_graph, in_graph_nodes, depth=1)
        in_graph_nodes = in_graph.nodes()
        counts += 1
        if counts > 5:
            break
    # print('after making bigger', in_graph.nodes(), len(in_graph.nodes()))
    return in_graph


def ged_computing(motifs, mg, depth=1, expand_hit=True, timeout=2, draw_pairs=False, draw_grid=False, save_fig=None):
    """
    :param expand_hit: To use if we want to compare the actual whole query with the expanded retrieve solutions
    """
    from tools.rna_ged_nx import ged
    res_dict = dict()
    all_motifs = [(motif_id, motif) for motif_id, motif in motifs.items()]
    for i, (motif_id, motif) in enumerate(all_motifs):
        motif_time = time.perf_counter()
        inner_dict = {}

        if motif_id != ('carnaval', '174'):
            continue

        # Get all relevant graphs, the border around the instance as well as a potential trimming
        print('attempting id : ', motif_id)
        query_instance = motif[0]
        query_whole_graph = whole_graph_from_node(query_instance[0])
        trimmed, trimmed_graph, actual_depth = trim_try(whole_graph=query_whole_graph, instance=query_instance,
                                                        depth=depth)
        query_instance_graph_expanded = induced_edge_filter(G=query_whole_graph, roots=query_instance)
        plot_depth = actual_depth + 1

        # For pretty plots, because too many nodes don't plot well
        # print('trimmed : ', trimmed)
        # print('expanding : ', actual_depth)
        # if len(trimmed) > 5:
        #     continue

        # Gives a hint of how trimming an instance works :
        # removing border nodes can remove more than the neighbors and
        # adding back the depth can add more than the original nodes
        # colors = ['red' if n in trimmed
        #           else 'blue' if n in query_instance
        # else 'grey' for n in expanded_graphs.nodes()]
        # rna_draw(g=expanded_graphs, node_colors=colors)
        # plt.show()
        # sys.exit()

        # Get the hits
        retrieved_instances = mg.retrieve_2(trimmed)
        sorted_hits = sorted(list(retrieved_instances.items()), key=lambda x: -x[1])

        if expand_hit:
            query_instance_graph = query_whole_graph.subgraph(query_instance)
        else:
            query_instance_graph = trimmed_graph

        if draw_grid or draw_pairs:
            trimmed_graph_expanded = induced_edge_filter(query_whole_graph, trimmed, depth=plot_depth)
            if not expand_hit:
                colors_query = ['red' if n in trimmed else 'grey' for n in trimmed_graph_expanded.nodes()]
                graph_plot_query = trimmed_graph_expanded
            else:
                colors_query = ['red' if n in trimmed else 'blue' if n in query_instance
                else 'grey' for n in query_instance_graph_expanded.nodes()]
                graph_plot_query = query_instance_graph_expanded
            if draw_grid:
                all_graphs = [graph_plot_query]
                all_colors = [colors_query]
                all_subtitles = ['Query']

        if draw_grid:
            plot_index = [0, 10, 100]
        else:
            plot_index = [0, 10, 100, 1000]
        for j in plot_index:
            # In case we have less than 1000 hits
            try:
                hit = sorted_hits[j][0]
            except IndexError:
                continue
            hit = [mg.reversed_node_map[node] for node in hit]
            hit_whole_graph = whole_graph_from_node(hit[0])

            # If one changes this, one should also remove the query expansion
            if expand_hit:
                hit_graph = induced_edge_filter(hit_whole_graph, hit, depth=actual_depth)
            else:
                hit_graph = hit_whole_graph.subgraph(hit)

            start = time.perf_counter()
            ged_value = ged(query_instance_graph, hit_graph, timeout=timeout)
            print(f"{j}-th hit, query : {len(query_instance_graph)}, hit : {len(hit_graph)}, "
                  f"ged value : {ged_value}, time : {time.perf_counter() - start:.2f}")
            inner_dict[j] = ged_value

            # TO PLOT THE HITS
            if draw_pairs or draw_grid:
                hit_graph_expanded = induced_edge_filter(hit_whole_graph, hit, depth=plot_depth)
                if not expand_hit:
                    # Just expand around the trims and hits
                    graph_plot_hit = hit_graph_expanded
                    colors_hit = ['red' if n in hit else 'grey' for n in graph_plot_hit.nodes()]
                else:
                    # Then expand again to have the trim, the border and the context
                    hit_graph_expanded_twice = induced_edge_filter(hit_whole_graph, hit, depth=plot_depth + 1)
                    graph_plot_hit = hit_graph_expanded_twice
                    colors_hit = ['red' if n in hit else 'blue' if n in hit_graph_expanded.nodes()
                    else 'grey' for n in graph_plot_hit.nodes()]
                if draw_pairs:
                    colors = [colors_query, colors_hit]
                    rna_draw_pair((graph_plot_query, graph_plot_hit), node_colors=colors, subtitles=('', ged_value))
                    plt.show()
                else:
                    all_graphs.append(graph_plot_hit.copy())
                    all_colors.append(colors_hit.copy())
                    all_subtitles.append(
                        f'{j}-th hit with Score : {sorted_hits[j][1]:2.2f} \n and GED : {ged_value:.1f}')

        if draw_grid:
            database, motif_number = motif_id
            rna_draw_grid(graphs=all_graphs, node_colors=all_colors, subtitles=all_subtitles,
                          save=save_fig, grid_shape=(2, 2))
            plt.show()
        # Pick another random that is not the current graph
        other_random = random.randint(0, len(all_motifs) - 2)
        if other_random >= i:
            other_random += 1
        random_query_instance = all_motifs[other_random][1][0]
        random_graph_whole = whole_graph_from_node(random_query_instance[0])
        random_graph = random_graph_whole.subgraph(random_query_instance)
        random_graph_0 = random_graph.copy()

        # Extra step to trim the other motif to get a similar size
        random_graph = match_sizes(graph_to_match=query_instance_graph,
                                   in_graph=random_graph,
                                   whole_in_graph=random_graph_whole)

        start = time.perf_counter()
        ged_value_random = ged(query_instance_graph, random_graph, timeout=timeout)
        print(f"random, query : {len(query_instance_graph)}, random : {len(random_graph)}, "
              f"ged value : {ged_value_random}, time : {time.perf_counter() - start:.2f}")
        ged_value_random_old = ged(query_instance_graph, random_graph_0, timeout=timeout)
        print(f"random_old, query : {len(query_instance_graph)}, random : {len(random_graph_0)}, "
              f"ged value : {ged_value_random_old}, time : {time.perf_counter() - start:.2f}")
        print()
        inner_dict['random_other'] = ged_value_random
        inner_dict['random_other_old'] = ged_value_random_old
        inner_dict['motif_time'] = time.perf_counter() - motif_time

        # TO PLOT THE RANDOM
        if draw_pairs:
            colors = [['red' if n in trimmed else 'grey' for n in query_instance_graph.nodes()],
                      ['grey' for _ in random_graph.nodes()]]
            subtitles = ('', ged_value_random)
            rna_draw_pair((query_instance_graph, random_graph), node_colors=colors, subtitles=subtitles)
            plt.show()

        print(inner_dict)
        res_dict[motif_id] = inner_dict

    return res_dict


def collapse_res_dict(res_dict, pruned_motifs):
    import pandas as pd
    df = pd.DataFrame()
    for motif, dict_value in res_dict.items():
        dict_value['motif'] = motif
        dict_value['motif_len'] = len(pruned_motifs[motif][0])
        df = df.append(dict_value, ignore_index=True)
    return df


if __name__ == '__main__':
    pass
    random.seed(0)
    from tools.utils import load_json

    import argparse

    parser = argparse.ArgumentParser()
    # parser.add_argument('--run', type=str, default="1hopmg")
    parser.add_argument('-r', '--run', type=str, default="new_kernel_1_unfiltered")
    args, _ = parser.parse_known_args()

    # Get pruned data : go through a motif file, and remove sparse ones (few instances),
    #   short ones (less than four nodes) or fully canonical ones.
    #   Then filter out the ones that are not in the NR data.
    #   The result is a pickle of a dict (dataset, motif_id): list of list of node ids.
    #   for instance :  ('carnaval', '258') : [['4pr6.B.122', '4pr6.B.161', '4pr6.B.162', ...], ...]
    # all_motifs = parse_json_new('../data/all_motifs_NR.json')
    # pruned_motifs = prune_motifs(all_motifs)
    # print(f'{len(pruned_motifs)}/{len(all_motifs)} motifs kept')
    # pickle.dump(pruned_motifs, open('../results/motifs_files/pruned_motifs_NR.p', 'wb'))
    pruned_motifs = pickle.load(open('../results/motifs_files/pruned_motifs_NR.p', 'rb'))
    # print(len(pruned_motifs))

    # Load meta-graph model
    model_name = f'../results/mggs/{args.run}.p'
    mgg = pickle.load(open(model_name, 'rb'))
    # nc, ec = mgg.statistics()
    # print(nc)
    # print(ec)

    # Use the retrieve to get A/B testing (or simply hit ratio)
    # all_failed, all_res = hit_ratio_all(pruned_motifs, mgg, max_instances_to_look_for=3)
    # results_dict = ab_testing(pruned_motifs, mgg)
    # pickle.dump(results_dict, open(f'../results/results_dict_{args.run}.p', 'wb'))
    # results_dict = pickle.load(open(f'../results/results_dict_{args.run}.p', 'rb'))
    # print(f"this is the result for {args.run}")
    # parse_ab_testing(results_dict)

    # Shuffle to get values as well as grid drawing.
    keys = list(pruned_motifs.keys())
    random.shuffle(keys)
    subsampled_shuffled = {k: pruned_motifs[k] for k in keys}
    res_dict_ged = ged_computing(motifs=subsampled_shuffled, mg=mgg,
                                 timeout=20, expand_hit=False, draw_grid=True)

    # Get GED values
    # res_dict_ged = ged_computing(motifs=pruned_motifs, mg=mgg,
    #                              timeout=100, expand_hit=False, draw_pairs=False, draw_grid=False)
    # pickle.dump(res_dict_ged, open(f'res_dict_ged_{args.run}.p', 'wb'))
    # res_dict_ged = pickle.load(open(f'res_dict_ged_{args.run}.p', 'rb'))

    # Parse the results with pandas. Filter out the timeouts.
    # import pandas as pd
    # pd.set_option('display.max_rows', None)
    # df_res = collapse_res_dict(res_dict_ged, pruned_motifs=pruned_motifs)
    # print(df_res.columns)
    # df_res = df_res.sort_values(by='motif_len', ascending=False)
    # print(df_res.columns)
    # df_res = df_res.sort_values(by=0, ascending=False)
    # df_res = df_res.sort_values(by='motif_time', ascending=False)
    # df_res = df_res[df_res['motif_time'] < 25]
    # pandas_results_print = df_res.groupby(['motif_len']).mean()
    # print(df_res)

    # # print(pandas_results_print)
    # print('number of motifs : ', len(df_res))
    # print(df_res.mean())
    # print(df_res.sem())
