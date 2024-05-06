#  from ablog.conf import *
from photon_platform.sphinxilator.global_conf import *
import photon_platform.curator as module

version = module.__version__

org = "photon-platform"
org_name = "photon-platform"

repo = "curator"
repo_name = "curator"

setup_globals(org, org_name, repo, repo_name)
