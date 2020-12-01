import glob
import asdf
import numpy as np
import sys
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import numpy.lib.recfunctions as rfn
import time
import gc
import os

from compaso_halo_catalog import CompaSOHaloCatalog
from tools.aid_asdf import save_asdf, reindex_particles

# TODO: copy halo info (just get rid of fields=fields_cat);  velocity interpolation (could be done when velocities are summoned, maybe don't interpolate); delete things properly; read parameters from header;

# want to show plots
want_plot = False

# location of the origin in Mpc/h
origin = np.array([-990.,-990.,-990.])

# simulation name
sim_name = "AbacusSummit_base_c000_ph006"
#sim_name = "AbacusSummit_highbase_c000_ph100"

# directory where the halo catalogs are saved
#cat_dir = "/mnt/store/lgarrison/"+sim_name+"/halos/"
cat_dir = "/mnt/store2/bigsims/"+sim_name+"/halos/"
#cat_dir = "/mnt/gosling2/bigsims/"+sim_name+"/halos/"

# directory where we save the final outputs
cat_lc_dir = "/mnt/gosling1/boryanah/light_cone_catalog/"+sim_name+"/halos_light_cones/"

# all merger tree redshifts
zs_mt = np.load("data/zs_mt.npy")


# all redshifts, steps and comoving distances of light cones files; high z to low z
zs_all = np.load("data_headers/redshifts.npy")
chis_all = np.load("data_headers/coord_dist.npy")
zs_all[-1] = float('%.1f'%zs_all[-1])

# get functions relating chi and z
chi_of_z = interp1d(zs_all,chis_all)
z_of_chi = interp1d(chis_all,zs_all)

# fields are we extracting from the catalogs
fields_cat = ['id','npstartA','npoutA','N','x_L2com','v_L2com','sigmav3d_L2com']

def extract_redshift(fn):
    red = float(fn.split('z')[-1][:5])
    return red

redshifts = glob.glob(cat_dir+"z*")
zs_cat = [extract_redshift(redshifts[i]) for i in range(len(redshifts))]
print(zs_cat)

# initial redshift where we start building the trees
#z_start = 0.3 # highbase
#z_stop = 0.65 # highbase
z_start = 0.5 # base
z_stop = 1.25 # base
ind_start = np.argmin(np.abs(zs_mt-z_start))
ind_stop = np.argmin(np.abs(zs_mt-z_stop))

# loop over each merger tree redshift
for i in range(ind_start,ind_stop+1):

    # starting snapshot
    z_in = zs_mt[i]
    z_cat = zs_cat[np.argmin(np.abs(z_in-zs_cat))]
    print("Redshift = %.3f %.3f"%(z_in,z_cat))
    
    # load the light cone arrays
    table_lc = np.load(os.path.join(cat_lc_dir,"z%.3f"%z_in,'table_lc.npy'))
    halo_ind_lc = table_lc['halo_ind']
    pos_interp_lc = table_lc['pos_interp']
    vel_interp_lc = table_lc['vel_interp']
    chi_interp_lc = table_lc['chi_interp']
    
    # catalog directory
    catdir = os.path.join(cat_dir,"z%.3f"%z_cat)
    
    # load halo catalog, setting unpack to False for speed
    cat = CompaSOHaloCatalog(catdir, load_subsamples='A_halo_pid', fields=fields_cat, unpack_bits = False)
    
    # in the event where we have more than one copies of the box, need to make sure that halo index is still within N_halo
    halo_ind_lc %= len(cat.halos)

    # halo catalog
    halo_table = cat.halos[halo_ind_lc]
    header = cat.header
    N_halos = len(cat.halos)
    print("N_halos = ",N_halos)

    # load the pid, set unpack_bits to True if you want other information
    pid = cat.subsamples['pid']
    npstart = halo_table['npstartA']
    npout = halo_table['npoutA']
    pid_new, npstart_new, npout_new = reindex_particles(pid,npstart,npout)        
    pid_table = np.empty(len(pid_new),dtype=[('pid',pid_new.dtype)])
    pid_table['pid'] = pid_new
    halo_table['npstartA'] = npstart_new
    halo_table['npoutA'] = npout_new

    # isolate halos that did not have interpolation and get the velocity from the halo info files
    not_interp = (np.sum(np.abs(vel_interp_lc),axis=1) - 0.) < 1.e-6
    vel_interp_lc[not_interp] = halo_table['v_L2com'][not_interp]
    print("percentage not interpolated = ",100.*np.sum(not_interp)/len(not_interp))
    
    # append new fields
    halo_table['index_halo'] = halo_ind_lc
    halo_table['pos_interp'] = pos_interp_lc
    halo_table['vel_interp'] = vel_interp_lc
    halo_table['redshift_interp'] = z_of_chi(chi_interp_lc)

    # save to files
    save_asdf(halo_table,"halo_info_lc",header,cat_lc_dir+"/z%4.3f/"%z_in)
    #save_asdf(pid_table,"pid_rv_lc",header,cat_lc_dir,z_in)
    # TESTING
    save_asdf(pid_table,"pid_lc",header,cat_lc_dir+"/z%4.3f/"%z_in)

    # delete things at the end
    del pid, pid_new, pid_table, npstart, npout, npstart_new, npout_new
    del halo_table
    del cat

    gc.collect()
    
#dict_keys(['HaloIndex', 'HaloMass', 'HaloVmax', 'IsAssociated', 'IsPotentialSplit', 'MainProgenitor', 'MainProgenitorFrac', 'MainProgenitorPrec', 'MainProgenitorPrecFrac', 'NumProgenitors', 'Position', 'Progenitors'])
