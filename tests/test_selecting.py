import psico.selecting
from pathlib import Path
from pymol import cmd

DATA_DIR = Path(__file__).resolve().parent / "data"
FILENAME_WITH_MSE = DATA_DIR / "2x19-frag-mse.pdb"


def test_select_range():
    cmd.reinitialize()
    cmd.fab("GASGAGS", "m1")
    cmd.select("s1", "resn ALA")
    psico.selecting.select_range()
    assert 4 == cmd.count_atoms("s1 & guide")
    psico.selecting.select_range("s2", "resn SER")
    assert 5 == cmd.count_atoms("s2 & guide")


def test_select_domains():
    cmd.reinitialize()
    cmd.load(FILENAME_WITH_MSE, "m1")
    psico.selecting.select_domains()
    assert cmd.get_names("all") == ["m1", "domain_B_132_137"]


# def select_pepseq(pattern, selection='all', name='sele', state=1, quiet=1,
# def select_nucseq(pattern, selection='all', name='sele', state=1, quiet=1):
# def select_sspick(selection, name=None, caonly=0, quiet=0):
# def diff(sele1, sele2, byres=1, name=None, operator='in', quiet=0):
# def symdiff(sele1, sele2, byres=1, name=None, operator='in', quiet=0):
# def collapse_resi(selection='(sele)', quiet=1):
# def wait_for(name, state=0, quiet=1):
# def select_distances(names='', name='sele', state=1, selection='all', cutoff=-1, quiet=1):
