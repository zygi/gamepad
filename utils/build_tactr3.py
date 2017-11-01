from enum import Enum
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.pyplot as plt

from parse_tacst2 import *


class TacEdge(object):
    def __init__(self, eid, tid, name, kind, ftac, src, tgt):
        self.eid = eid
        self.tid = tid
        self.name = name
        self.kind = kind
        self.ftac = ftac
        self.src = src
        self.tgt = tgt

    def __str__(self):
        return "({}, {}, {}, {} -> {})".format(self.eid, self.tid, self.name, self.src, self.tgt)

class TacTreeBuilder(object):
    def __init__(self, tacs, eid=0, solvgid=0, errgid=0, f_log=True):
        for tac in tacs:
            assert isinstance(tac, RawTac)

        self.tacs = tacs
        self.it_tacs = MyIter(tacs)
        self.f_log = f_log
        
        self.eid = eid
        self.solvgid = solvgid
        self.errgid = errgid
        self.numtacs = 0
        self.edges = []
        self.graph = nx.MultiDiGraph()
        self.notok = []

    def _mylog(self, msg, f_log=False):
        if f_log or self.f_log:
            # self.log.append(msg)
            print(msg)

    def _add_edges(self, edges):
        self.edges += edges
        for edge in edges:
            self.graph.add_edge(edge.src, edge.tgt, key=edge.eid)

    def _fresh_eid(self):
        eid = self.eid
        self.eid += 1
        return eid

    def _fresh_errgid(self):
        errgid = self.errgid
        self.errgid += 1
        return "e" + str(errgid)

    def _fresh_solvgid(self):
        solvgid = self.solvgid
        self.solvgid += 1
        return "t" + str(solvgid)

    def _launch_rec(self, tacs):
        tr_builder = TacTreeBuilder(tacs, eid=self.eid,
                                    solvgid=self.solvgid, errgid=self.errgid)
        tr_builder.build_tacs()
        self.eid = tr_builder.eid
        self.solvgid = tr_builder.solvgid
        self.errgid = tr_builder.errgid
        self.notok += tr_builder.notok
        self.numtacs += tr_builder.numtacs
        return tr_builder.edges, tr_builder.graph

    def _is_terminal(self, decl):
        return decl.hdr.gid == GID_SOLVED or decl.hdr.mode == "afterE"

    def _mk_edge(self, tac, bf_decl, af_decl):
        if af_decl.hdr.gid == GID_SOLVED:
            edge = TacEdge(self._fresh_eid(), tac.uid, tac.name,
                           tac.kind, bf_decl.hdr.ftac,
                           bf_decl.hdr.gid, self._fresh_solvgid())
        elif af_decl.hdr.mode == "afterE":
            edge = TacEdge(self._fresh_eid(), tac.uid, tac.name,
                           tac.kind, bf_decl.hdr.ftac,
                           bf_decl.hdr.gid, self._fresh_errgid())
        else:
            edge = TacEdge(self._fresh_eid(), tac.uid, tac.name,
                           tac.kind, bf_decl.hdr.ftac,
                           bf_decl.hdr.gid, af_decl.hdr.gid)
        return edge

    def _mk_edge2(self, tac, bf_decl, gid):
        edge = TacEdge(self._fresh_eid(), tac.uid, tac.name,
                       tac.kind, bf_decl.hdr.ftac,
                       bf_decl.hdr.gid, gid)
        return edge

    def build_atomic(self):
        # Internal
        it_tacs = self.it_tacs
        self._mylog("@build_atomic:before<{}>".format(it_tacs.peek()))
        self.numtacs += 1

        tac = next(it_tacs)
        nbf = len(tac.bf_decls)
        naf = len(tac.af_decls)
        edges = []
        if nbf == naf:
            for bf_decl, af_decl in zip(tac.bf_decls, tac.af_decls):
                edges += [self._mk_edge(tac, bf_decl, af_decl)]
        elif naf % nbf == 0:
            # Compute branching ratio
            nbod = len(tac.bods)
            af2bf = int(naf / nbf)

            for i in range(0, nbf):
                start = i * af2bf
                end = i * af2bf + af2bf
                bf_decl = tac.bf_decls[i]
                for af_decl in tac.af_decls[start:end]:
                    edges += [self._mk_edge(tac, bf_decl, af_decl)]
        else:
            self.notok += [tac]

        self._add_edges(edges)

    def build_name(self):
        # Internal
        it_tacs = self.it_tacs
        self._mylog("@build_name:before<{}>".format(it_tacs.peek()))
        self.numtacs += 1

        tac = next(it_tacs)
        nbf = len(tac.bf_decls)
        naf = len(tac.af_decls)
        edges = []
        if nbf == naf:
            for bf_decl, af_decl in zip(tac.bf_decls, tac.af_decls):
                edges += [self._mk_edge(tac, bf_decl, af_decl)]
        else:
            self.notok += [tac]

        self._add_edges(edges)

    def build_notation(self):
        # Internal
        it_tacs = self.it_tacs
        self._mylog("@build_notation:before<{}>".format(it_tacs.peek()))
        self.numtacs += 1

        tac = next(it_tacs)
        for bf_decl, body in zip(tac.bf_decls, tac.bods):
            # 1. connect up body
            edges, _ = self._launch_rec(body)

            # TODO(deh): Skip notation?
            # TODO(deh): check for weirdness here
            # Accumulate changes
            self._add_edges(edges)

    def _direct_connect(self):
        pass

    def build_ml(self):
        # Internal
        it_tacs = self.it_tacs
        self._mylog("@build_ml:before<{}>".format(it_tacs.peek()))
        self.numtacs += 1

        tac = next(it_tacs)
        body = tac.bods[0]

        if tac.name.startswith("<coretactics::intro@0>") or \
           tac.name.startswith("<g_auto::auto@0>"):
            # 1-1
            if len(tac.bf_decls) == 1 and len(tac.af_decls) == 1:
                edges = []
                for bf_decl, af_decl in zip(tac.bf_decls, tac.af_decls):
                    edges += [self._mk_edge(tac, bf_decl, af_decl)]
                # Accumulate changes
                self._add_edges(edges)
            else:
                self.notok += [tac]
        elif tac.name.startswith("<ssreflect_plugin::ssrcase@0>") or \
             tac.name.startswith("<ssreflect_plugin::ssrapply@0>"):
            # 1-n
            if len(tac.bf_decls) == 1:
                edges = []
                bf_decl = tac.bf_decls[0]
                for af_decl in tac.af_decls:
                    edges += [self._mk_edge(tac, bf_decl, af_decl)]
                self._add_edges(edges)
            else:
                self.notok += [tac]
        elif tac.name.startswith("<ssreflect_plugin::ssrhave@0>"):
            # 1. connect up body
            body_edges, body_graph = self._launch_rec(body)

            # 2. connect up body to top-level
            edges = []
            if body_edges:
                for bf_decl in tac.bf_decls:
                    edges += [self._mk_edge2(tac, bf_decl, body_edges[0].src)]

            # 3. connect me up
            if len(tac.bf_decls) == 1 and len(tac.af_decls) == 1:
                edges += [self._mk_edge(tac, tac.bf_decls[0], tac.af_decls[0])]
            else:
                self.notok += [tac]

            # Accumulate changes
            self._add_edges(body_edges)
            self._add_edges(edges)
        else:
            # 1. connect up body
            body_edges, body_graph = self._launch_rec(body)

            # 2. connect up top-level before/after
            edges = []
            has_path = [0 for _ in range(len(tac.bf_decls))]
            for i, bf_decl in enumerate(tac.bf_decls):
                for af_decl in tac.af_decls:
                    try:
                        if nx.has_path(body_graph, bf_decl.hdr.gid, af_decl.hdr.gid):
                            edges += [self._mk_edge(tac, bf_decl, af_decl)]
                            has_path[i] += 1
                            break
                    except nx.exception.NodeNotFound:
                        has_path[i] += 1

            # Accumulate changes
            self._add_edges(body_edges)
            self._add_edges(edges)

            # TODO(deh): some ML tactics will not have a path
            # Check for weirdness
            if any(x == 0 for x in has_path):
                self.notok += [tac]

    """
    def _connect_bfaf(self, tac):
        it_tacs = MyIter(self.tacs)
        while it_tacs.has_next():
            tac_p = next(it)
            for af_decl in tac.af_decls:
                for bf_decl in tac_p.bf_decls:
                    if af_decl.hdr.gid == bf_decl.hdr.gid:
                        self
    """

    def build_tacs(self):
        # Internal
        it_tacs = self.it_tacs
        
        while it_tacs.has_next():
            tac = it_tacs.peek()
            if tac.kind == TacKind.ATOMIC:
                self.build_atomic()
            elif tac.kind == TacKind.NAME:
                self.build_name()
            elif tac.kind == TacKind.ML:
                self.build_ml()
            elif tac.kind == TacKind.NOTATION:
                self.build_notation()
            else:
                raise NameError("TacKind {} not supported".format(tac.kind))

    def show(self):
        print("Graph edges:\n", "\n".join(map(str, self.graph.edges)))
        print("TacEdges:\n", "\n".join(map(str, self.edges)))
        if self.graph.edges:
            nx.drawing.nx_pylab.draw_kamada_kawai(self.graph, with_labels=True)
            plt.show()