'''
(c) 2010-2012 Thomas Holder, MPI for Developmental Biology

License: BSD-2-Clause
'''

from pymol import cmd, CmdException

_auto_arg0_align = cmd.auto_arg[0]['align']
_auto_arg1_align = cmd.auto_arg[1]['align']
_auto_arg1_select = cmd.auto_arg[1]['select']


def _assert_package_import():
    if not __name__.endswith('.selecting'):
        raise CmdException("Must do 'import psico.selecting' instead of 'run ...'")


def select_pepseq(pattern, selection='all', name='sele', state=1, quiet=1,
        cutoff=4.0, one_letter=None, *, _self=cmd):
    '''
DESCRIPTION

    Find a amino acid sequence pattern (regular expression) in given atom
    selection. Does not span gaps (unless matched by a wildcard).

USAGE

    select_pepseq pattern [, selection [, name [, state ]]]

ARGUMENTS

    pattern = string: amino acid sequence in one letter code, can be a
    regular expression pattern.

    selection = string: atom selection of protein (non protein atoms in
    selection are silently ignored) {default: all})

    name = a unique name for the selection {default: sele}

EXAMPLE

    fetch 1a00, async=0
    select_pepseq AL[EG]R, chain A+B, sele1
    select_pepseq ([LIVAM]{3,}), all, sele2

SEE ALSO

    There is the pepseq/ps. selection operator. Example:
    select actsite, protein and ps. ADFG

    Similar scripts:
    http://pldserver1.biochem.queensu.ca/~rlc/work/pymol/seq_select.py
    http://pymolwiki.org/index.php/FindSeq
    '''
    import re
    from chempy import cpv

    if not one_letter:
        _assert_package_import()
        from . import one_letter

    state, quiet = int(state), int(quiet)
    cutoff = float(cutoff)

    seq_list = []
    idx_list = []
    prev = [1e300, 1e300, 1e300]

    def callback(model, index, resn, coord):
        if cpv.distance(coord, prev) > cutoff:
            seq_list.append('#')
            idx_list.append(None)
        seq_list.append(one_letter.get(resn, '#'))
        idx_list.append((model, index))
        prev[:] = coord

    _self.iterate_state(state, '(%s) and guide' % (selection),
            'callback(model, index, resn, (x, y, z))', space=locals())

    matches = list(re.finditer(pattern.upper(), ''.join(seq_list)))
    if not quiet:
        if len(matches) == 0:
            print(' select_pepseq: Pattern not found in selection')
        else:
            print(' select_pepseq: Pattern found %d time(s)' % (len(matches)))

    sel_list = []
    for m in matches:
        start, stop = m.span()
        sel_list.extend('%s`%d' % idx for idx in idx_list[start:stop] if idx is not None)

    return _self.select(name, '(' + selection + ') and byres (none ' + ' '.join(sel_list) + ')')


def select_nucseq(pattern, selection='all', name='sele', state=1, quiet=1, *, _self=cmd):
    '''
DESCRIPTION

    Find a nucleic acid sequence pattern in given atom selection.
    '''
    one_letter = dict(["AA", "CC", "TT", "GG", "UU"])
    return select_pepseq(pattern, selection, name, state, quiet, 6.5, one_letter, _self=_self)


def select_sspick(selection, name=None, caonly=0, quiet=0, *, _self=cmd):
    '''
DESCRIPTION

    Extend selection by connected secondary structure elements.

    Also available as wizard (type: "wizard sspick").

USAGE

    select_sspick selection [, name [, caonly [, quiet ]]]

ARGUMENTS

    selection = string: selection-expression

    name = string: create a named atom selection if not None {default: None}
    '''
    caonly, quiet = int(caonly), int(quiet)

    qkeys = set()
    _self.iterate('bycalpha (%s)' % (selection),
            'qkeys.add(((model,segi,chain,ss), resv))', space={'qkeys': qkeys})

    def in_intervals(i, intervals):
        for interval in intervals:
            if interval[0] <= i <= interval[1]:
                return True
        return False

    elements = dict()
    for key, resv in qkeys:
        element = elements.setdefault(key, [])
        if in_intervals(resv, element):
            continue
        resv_set = set()
        _self.iterate('/%s/%s/%s//CA and ss "%s"' % key, 'resv_set.add(resv)',
                space={'resv_set': resv_set})
        resv_min = resv
        resv_max = resv
        while (resv_min - 1) in resv_set:
            resv_min -= 1
        while (resv_max + 1) in resv_set:
            resv_max += 1
        element.append((resv_min, resv_max))

    sele_list = []
    ss_names = {'S': 'Strand', 'H': 'Helix', '': 'Loop', 'L': 'Loop'}
    for key in elements:
        model, segi, chain, ss = key
        for resv_min, resv_max in elements[key]:
            sele = '/%s/%s/%s/%d-%d' % (model, segi, chain, resv_min, resv_max)
            if caonly:
                sele += '/CA'
            sele_list.append(sele)
            if not quiet:
                print("%-6s %s" % (ss_names.get(ss, ss), sele))

    sele = ' '.join(sele_list)
    if name is not None:
        _self.select(name, sele)
    elif not quiet:
        print(' Selection: ' + sele)

    return sele


def diff(sele1, sele2, byres=1, name=None, operator='in', quiet=0, *, _self=cmd):
    '''
DESCRIPTION

    Difference between two molecules

ARGUMENTS

    sele1 = string: atom selection

    sele2 = string: atom selection

    byres = 0/1: report residues, not atoms (does not affect selection)
    {default: 1}

    operator = in/like/align: operator to match atoms {default: in}

SEE ALSO

    symdiff
    '''
    byres, quiet = int(byres), int(quiet)
    if name is None:
        name = _self.get_unused_name('diff')
    if operator == 'align':
        alnobj = _self.get_unused_name('__aln')
        _self.align(sele1, sele2, cycles=0, transform=0, object=alnobj)
        sele = '(%s) and not %s' % (sele1, alnobj)
        _self.select(name, sele)
        _self.delete(alnobj)
    else:
        sele = '(%s) and not ((%s) %s (%s))' % (sele1, sele1, operator, sele2)
        _self.select(name, sele)
    if not quiet:
        if byres:
            seleiter = 'byca ' + name
            expr = 'print("/%s/%s/%s/%s`%s" % (model,segi,chain,resn,resi))'
        else:
            seleiter = name
            expr = 'print("/%s/%s/%s/%s`%s/%s" % (model,segi,chain,resn,resi,name))'
        _self.iterate(seleiter, expr)
    return name


def symdiff(sele1, sele2, byres=1, name=None, operator='in', quiet=0, *, _self=cmd):
    '''
DESCRIPTION

    Symmetric difference between two molecules

SEE ALSO

    diff
    '''
    byres, quiet = int(byres), int(quiet)
    if name is None:
        name = _self.get_unused_name('symdiff')
    tmpname = _self.get_unused_name('__tmp')
    diff(sele1, sele2, byres, name, operator, quiet)
    diff(sele2, sele1, byres, tmpname, operator, quiet)
    _self.select(name, tmpname, merge=1)
    _self.delete(tmpname)
    return name


def collapse_resi(selection='(sele)', quiet=1, *, _self=cmd):
    '''
DESCRIPTION

    Returns a compact selection macro for the given selection on
    residue number (resi) level.

    Rewrite of http://pymolwiki.org/index.php/CollapseSel

ARGUMENTS

    selection = string: atom selection {default: (sele)}
    '''
    from collections import defaultdict
    s_dict = defaultdict(set)
    _self.iterate(selection, 's_dict[model,segi,chain].add(resv)', space=locals())
    r_all = []
    for key, s in s_dict.items():
        s = sorted(s)
        r = [[s[0], s[0]]]
        for i in s[1:]:
            if i <= r[-1][1] + 1:
                r[-1][1] = i
            else:
                r.append([i, i])
        resi = '+'.join(('%d-%d' % (f, t) if f != t else '%d' % (f)) for (f, t) in r)
        r_all.append('/%s/%s/%s/' % key + resi)
    if not int(quiet):
        for r in r_all:
            print(' collapse_resi: ' + str(r))
    return ' '.join(r_all)


def wait_for(name, state=0, quiet=1, *, _self=cmd):
    '''
DESCRIPTION

    Wait for "name" to be available as selectable object.
    '''
    if _self.count_atoms('?' + name, 1, state) == 0:
        s = _self.get_setting_boolean('suspend_updates')
        if s:
            _self.set('suspend_updates', 0)
        _self.refresh()
        if s:
            _self.set('suspend_updates')


def select_distances(names='', name='sele', state=1, selection='all', cutoff=-1, quiet=1, *, _self=cmd):
    '''
DESCRIPTION

    Turns a distance object into a named atom selection.

ARGUMENTS

    names = string: names of distance objects (no wildcards!) {default: all
    measurement objects}

    name = a unique name for the selection {default: sele}

    state = int: object state (-1: current, 0: all states) {default: 1}

SEE ALSO

    get_raw_distances
    '''
    from collections import defaultdict
    _assert_package_import()
    from .querying import get_raw_distances

    state, cutoff, quiet = int(state), float(cutoff), int(quiet)
    states = [state] if state else list(range(1, _self.count_states(selection) + 1))

    sele_dict = defaultdict(set)
    for state in states:
        distances = get_raw_distances(names, state, selection, _self=_self)
        for idx1, idx2, dist in distances:
            if cutoff <= 0.0 or dist <= cutoff:
                sele_dict[idx1[0]].add(idx1[1])
                sele_dict[idx2[0]].add(idx2[1])

    _self.select(name, 'none')
    tmp_name = _self.get_unused_name('_')

    r = 0
    for model in sele_dict:
        _self.select_list(tmp_name, model, list(sele_dict[model]), mode='index')
        r = _self.select(name, tmp_name, merge=1)
        _self.delete(tmp_name)

    if not quiet:
        print(' Selector: selection "%s" defined with %d atoms.' % (name, r))
    return r


def select_range(name="", selection="", merge=1, *, _self=cmd):
    """
DESCRIPTION

    Select all atoms between the first and last atom in the
    current (or given) selection.

ARGUMENTS

    name = str: Named selection to create {default: current active selection}

    selection = str: Selection expression {default: name}
    """
    if not name:
        name = _self.get_names("selections", enabled_only=1)[0]

    if not selection:
        selection = name

    tmpsele = _self.get_unused_name("_tmpsele")
    _self.select(tmpsele, selection)

    try:
        for model in _self.get_object_list(tmpsele):
            idx_first = _self.index(f"first (%{model} & {tmpsele})")[0]
            idx_last = _self.index(f"last (%{model} & {tmpsele})")[0]
            assert idx_first[0] == idx_last[0]
            _self.select(name,
                       f"%{model} & index {idx_first[1]}-{idx_last[1]}",
                       merge=merge)
            merge = 1
    finally:
        _self.delete(tmpsele)


def select_domains(selection: str = "all",
                   prefix: str = "domain",
                   minsize: int = 70,
                   method="mean",
                   cutoff: float = 999.9,
                   quiet: bool = True,
                   *,
                   _self=cmd) -> list:
    """
DESCRIPTION

    Make domain selections based on a contact matrix heuristic.

ARGUMENTS

    selection = str: Atom selection {default: all}

    prefix = str: Prefix for selection names {default: domain}

    minsize = int: Minimum size of a domain in residues

    method = mean|max: Function for partitioning the distance matrix

    cutoff = float: Partitioning cutoff
    """
    import numpy
    from .numeric import pdist_squareform
    from .querying import iterate_to_list
    from .querying import object_chain_iter

    func = {'max': numpy.max, 'mean': numpy.mean, 'sum': numpy.sum}[method]
    minsize = int(minsize)
    cutoff = float(cutoff)
    quiet = int(quiet)
    names = []

    def gen(start, end):
        for i in range(start + minsize, end - minsize):
            yield (func(dist_mat[:i, :i]) + func(dist_mat[i:, i:]), i)

    def gen_all(start, end):
        try:
            d0, j0 = min(gen(start, end))
        except ValueError:
            return

        if d0 > cutoff:
            return

        yield (d0, j0)
        yield from gen_all(start, j0)
        yield from gen_all(j0, end)

    for model, chain in object_chain_iter(selection, _self=_self):
        sele = f'({selection}) & /{model}//{chain} & guide'

        X = _self.get_coords(sele)
        if X is None:
            continue

        dist_mat = pdist_squareform(X)

        N = X.shape[0]
        partitions = list(gen_all(0, N))
        boundaries = [0] + sorted(j for (d, j) in partitions) + [N]

        idx2macro = dict(
            iterate_to_list(
                sele,
                '((model, index), f"/{model}/{segi}/{chain}/{resn}`{resi}")'))

        idx2resi = dict(iterate_to_list(sele, '((model, index), resi)'))
        idx_list = _self.index(sele)

        for (i, j) in zip(boundaries[:-1], boundaries[1:]):
            idxi, idxj = idx_list[i], idx_list[j - 1]
            name = _self.get_unused_name(
                f"{prefix}_{chain}_{idx2resi[idxi]}_{idx2resi[idxj]}",
                alwaysnumber=0)
            assert idxi[0] == model
            _self.select(name,
                         f"model {idxi[0]} & byres index {idxi[1]}-{idxj[1]}",
                         0)

            if not quiet:
                print(f" {name:20} {idx2macro[idxi]:20} {idx2macro[idxj]}")

            names.append(name)

        if not quiet:
            print(" Partitions:")
            for (d, i) in sorted(partitions):
                print(f" {d:4.2f} {idx2macro[idx_list[i]]}")

    return names


class select_temporary:
    '''
DESCRIPTION

    Context manager for creating a temporary named selection.

    >>> with select_temporary(sele_expr) as named_sele:
    ...     assert named_sele in cmd.get_names()
    '''

    def __init__(self, sele, prefix="_sele", *, _self=cmd):
        self._self = _self
        self.sele = sele
        self.prefix = prefix

    def __enter__(self):
        self.name = self._self.get_unused_name(self.prefix)
        self._self.select(self.name, self.sele)
        return self.name

    def __exit__(self, type, value, traceback):
        self._self.delete(self.name)


# commands
cmd.extend('select_pepseq', select_pepseq)
cmd.extend('select_nucseq', select_nucseq)
cmd.extend('select_sspick', select_sspick)
cmd.extend('symdiff', symdiff)
cmd.extend('diff', diff)
cmd.extend('collapse_resi', collapse_resi)
cmd.extend('select_distances', select_distances)
cmd.extend('select_range', select_range)
cmd.extend('select_domains', select_domains)

# autocompletion
cmd.auto_arg[0].update([
    ('select_sspick', _auto_arg0_align),
    ('symdiff', _auto_arg0_align),
    ('diff', _auto_arg0_align),
    ('collapse_resi', cmd.auto_arg[0]['zoom']),
    ('select_distances', [
        lambda: cmd.Shortcut(cmd.get_names_of_type('object:measurement')),
        'distance object', '']),
    ('select_domains', cmd.auto_arg[0]['align']),
])
cmd.auto_arg[1].update([
    ('select_pepseq', _auto_arg1_select),
    ('select_nucseq', _auto_arg1_select),
    ('symdiff', _auto_arg1_align),
    ('diff', _auto_arg1_align),
    ('select_range', _auto_arg1_select),
])

# vi:expandtab:smarttab
