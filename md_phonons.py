#/usr/bin/env python3
import numpy as np
import time
t_start = time.time()
print("start","Time: 0 seconds\n")
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from numba import njit,prange


plt.style.use('ggplot')

# parameters
folder_path='with_lammps/'
save_flag= '_10K_1fs'
trajectory_file = "traj_lammps_10K_1fs.xyz"
# folder_path=''
# save_flag= ''
# trajectory_file = "traj_unwrapped.xyz"

sigma_true = 3.4e-10  # m ## This is necessarily to get rid of lj units
kB_true = 1.38064852e-23  #m2 kg s-2 K-1
T = 10
mass = 6.6335209e-26  #kg
# notation
# l,l' -> refers to the unit cell in the supercell
# k,k' -> runs over all Natoms
# \alpha, \beta -> x,y,z

# cell = np.ones((3,3))
# number of repeats

# origin of l-th unit cell relative to l=[0,0,0]

# @njit()
# def np_apply_along_axis(func1d, axis, arr):
#   assert arr.ndim == 2
#   assert axis in [0, 1]
#   if axis == 0:
#     result = np.empty(arr.shape[1],dtype=np.complex128)
#     for i in range(len(result)):
#       result[i] = func1d(arr[:, i])
#   else:
#     result = np.empty(arr.shape[0],dtype=np.complex128)
#     for i in range(len(result)):
#       result[i] = func1d(arr[i, :])
#   return result

# @njit(parallel=True)
# def np_mean(array, axis):
#   return np_apply_along_axis(np.mean, axis, array)

@njit(parallel=True)
def mean(arr):
	summation = np.zeros((arr.shape[1],arr.shape[2]),dtype=np.complex128)
	for frame in prange(arr.shape[0]):
		for j in prange(arr.shape[1]):
			summation[j,:] += arr[frame,j,:]
	return summation

# def read_xyz(pos=folder_path+trajectory_file):
# 	""" Reads .xyz file and create a frame-indexed trajectory array."""
# 	with open(pos,"r") as f:
# 		Natoms,Nframes = 0,0
# 		lines = f.readlines()
# 		frame = 0
# 		k = 0
# 		counter = 0
# 		traj_built_flag = True
# 		for idx,ln in enumerate(lines):
# 			if counter==0:
# 				if traj_built_flag :
# 					Natoms = int(ln)
# 					Nframes = int(len(lines)/(Natoms+2))
# 					traj = np.zeros((Nframes,Natoms,4),dtype=np.float64)
# 					traj_built_flag = False
# 				counter += 1
# 			elif counter==1:
# 				k = 0 # atom idx
# 				counter +=1 
# 			elif counter>1:
# 				# print [float(l) for l in ln.split()]
# 				traj[frame,k,:] = [float(l) for l in ln.split()]
# 				# print traj[frame,k,:]
# 				k += 1
# 				counter += 1
# 				if counter==(Natoms+2):
# 					# print Natoms, ln
# 					counter = 0
# 					frame += 1
# 	print("Trajectory read!","Time (seconds): ",time.time()-t_start)
# 	return traj,Natoms,Nframes


# @njit()
def equidist(p1, p2, npoints=20):
	""" Creates an array of equidistant points between two N-dim points."""
	temp = np.zeros((npoints,p1.shape[0]),dtype=np.float64)
	# loop over x,y,z dimensions
	for i in range(p1.shape[0]):
		temp[:,i] = np.linspace(p1[i],p2[i],npoints)
	return temp

# @njit()
def highsymm_path(symm_points,l):
	""" Generates high symmetry path 
	along the given points."""

	# K_step = 2 * np.pi / (a * l[0])
	l0_rev = 1.0 / l[0]

	folder_pathdiff_symm_points = np.diff(symm_points, axis=0)
	path = np.array(symm_points[0],ndmin=2)
	for ii in range(folder_pathdiff_symm_points.shape[0]):
		for jj in range(l[0]):
			path = np.append(path,[path[-1] + folder_pathdiff_symm_points[ii] * l0_rev], axis=0)

	return path


def plot_disp(bands):
	""" Plots phonon dispersion.
	bands shape: No. bands x No. path points x No. dimensions"""
	x = np.arange(0,bands.shape[1])
	for band_i in range(bands.shape[0]):
		en = bands[band_i,:,0]
		plt.plot(x,en)
	plt.show()
#	plt.savefig('phonon_dispersion.pdf')
	return None


@njit(parallel=True)
def exponential_term(traj_0,pt):
	exponentials = np.zeros((nuq, Natoms), dtype=np.complex128)
	for ii in prange(nuq):
		exponentials[ii] = np.exp(-1j * np.sum(pt[ii] * traj_0, axis=1))
	print("exponentials calculated")
	return exponentials


@njit(parallel=True)
def FT(POS,exponentials,pt):
	'''
	Calculate Fourier transform of position. ONLY for 1 FRAME
	:param traj: in this dimension: POS[natom,3]
	:param pt: high symmetry path
	:return:
	'''
	# print "POS",POS
	kir = np.zeros((nuq,3),dtype=np.complex128)
	if len(POS.shape) != 2:
		raise ValueError

	for ii in prange(nuq):
		# exponential = np.exp(-1j * np.sum(pt[ii] * POS, axis=1))
		# print  np.sum(POS[:,0] * exponential)
		# kir[ii,0] = Natoms_root_rev*np.sum( POS[:,0] * exponential )
		# kir[ii,1] = Natoms_root_rev*np.sum( POS[:,1] * exponential )
		# kir[ii,2] = Natoms_root_rev*np.sum( POS[:,2] * exponential )

		kir[ii,0] = Natoms_root_rev*np.sum( POS[:,0] * exponentials[ii])
		kir[ii,1] = Natoms_root_rev*np.sum( POS[:,1] * exponentials[ii])
		kir[ii,2] = Natoms_root_rev*np.sum( POS[:,2] * exponentials[ii])
	return kir


@njit(parallel=True)
def greens_func(traj,traj_for_FT,pt):
	"""	Takes the Fourier transform of the absolute positions for a given vector.
	Averages all frames and calculates the FT Green's function coeffs at each 
	wave vector q."""
	# R_ka = np.mean(traj,axis=0) # average over all frames

	G_ft = np.zeros((nuq,3,3),dtype=np.complex128) # ka, k'b

	# Calculate exponential term necessarily for FT calculation
	exponentials = exponential_term(traj_for_FT, pt)
	# For first term
	for fram in range(Nframes):
		Rq      =  FT(traj[fram],exponentials,pt)
		Rq_star =  np.conj(Rq)
		for qq in prange(nuq):
			for alpha in range(3):
				for beta in range(3):
					G_ft[qq,alpha,beta] += Rq[qq,alpha]*Rq_star[qq,beta]
					# print G_ft[qq]
	G_ft=G_ft*(1.0/Nframes)
	# print("Green function first term is done!","Time (seconds): ",time.time()-t_start)
	# For Second term
	# R_mean = np.mean(traj,axis=0)
	# R_mean = np_mean(traj,0)
	R_mean = mean(traj)


	R_mean_q = FT(R_mean,exponentials,pt)
	R_mean_q_star = np.conj(R_mean_q)

	for qq in prange(nuq):
		for alpha in prange(3):
			for beta in prange(3):
				G_ft[qq,alpha, beta] -= R_mean_q[qq, alpha] * R_mean_q_star[qq, beta]

	# print("Green function Second term is done!","Time (seconds): ",time.time()-t_start)
	print("Green function constructed!")
	print("G_ft.shape=",G_ft.shape)
	return G_ft

# @njit(parallel=True)
def force_constants(G):
	""" Calculates force constants $\Phi_{lk\alpha,l'k'\beta}$ """
	# phi = np.zeros(np.shape(G))
	# check if G is hermitian 
	# !! PROBLEM should check for all atoms separately
	for qq in prange(G.shape[0]):
		if (np.round(np.transpose(np.conj(G[qq])),4)==np.round(G[qq],4)).all(): # check if G is hermitian
			# print(G[qq])
			print("Matrix is Hermitian, and Determinant is=",np.linalg.det(G[qq]))
			if 
		else:
			# print("Matrix is NOT Hermitian\n",np.conj(G)==G)
			print("Matrix is NOT Hermitian for q_n=",qq)
			# print "G.conj is :\n",np.conj(G[qq])
			print("G is :\n",G[qq][0])
			print("G is :\n",G[qq][1])
			print("G is :\n",G[qq][2])
			#exit()
	# 	phi = k_B * T* G
	# else:

	#### FROM EQ. 17 of the phonons paper
	Phi = np.zeros(G.shape,dtype=np.complex128) # ka, k'b
	for qq in range(G.shape[0]):
		Phi[qq] = np.linalg.inv(G[qq])
	####
	return Phi

# @njit(parallel=True)
def eigenfreqs(phi_ft,nuq):
	# D = 1/np.sqrt(M*M)* phi_ft
	D = phi_ft
	omega_sq = np.zeros((nuq,3),dtype=np.float64)
	for qq in prange(nuq):
		# eigenvals,eigenvecs = np.linalg.eigh(D[qq])
		eigenvals = np.linalg.eigvals(D[qq])
		eidx = eigenvals.argsort()[::-1]   # sorting from smallest to largest
		eigenvals = eigenvals[eidx]
		print("== EIGENVALUES ==\n",eigenvals)
		omega_sq[qq] = eigenvals
	print("Success!")
	## Convert to SI units ==>>Hz
	omega_sq *= kB_true*T/(mass*sigma_true*sigma_true)
	print("Frequencies converted to Hz")
	return np.sqrt(omega_sq)

# @njit(parallel=False)
def ASR(phi,pgp,nucell):
	"""
	:param phi: is Force matrix at q=0
	:param nucell: is number of atoms in unitcell, For the time being it works only for nucell==1
	:return: ASRed phi_0
	"""
	if nucell != 1: raise ReferenceError

	for ii in pgp:
		phi[ii] = np.imag(phi[ii])*1j  # Zeroing phi at Gamma point (call me Neven, if you complain :)
	return phi


def main():
	global Natoms
	global Natoms_root_rev
	global Nframes
	global nuq


	load_previous_calculation = False
	# load_previous_calculation = True
	# load_loaded_traj=True
	load_loaded_traj=False

	# set some initial values
	a = np.power(2,(2./3)) # cubic constant in sigma units
	skip_portion =  10 #skip this percent of total time step at the begining
	l = np.array([3, 3, 3])  # lattice size in each direction. THEY MUST BE EQUAL!

	# Defining high symmetry points in Kx,Ky,Kz direction ref of the path: http://lampx.tugraz.at/~hadley/ss1/bzones/fcc.php
	gamma = np.array([0,0,0])
	X = np.array([0,2*np.pi/a,0])
	W = np.array([np.pi/a,2*np.pi/a,0])
	K =  np.array([3*np.pi/(2*a),3*np.pi/(2*a),0])
	L = np.array([np.pi/a,np.pi/a,np.pi/a])	
	U = np.array([np.pi/(2*a),2*np.pi/a,np.pi/(2*a)])

	# pt = highsymm_path(np.array([K,gamma,L,W,X,U,X,gamma]),l) # make a path of all points
	# pgp = np.array([1,7])*l[0]  # position of gamma points for ASR  Manually for the time being! ==> Just put index of where gamma points is in pt.
	# plot_ticks = ['K', r'$\Gamma$', 'L', 'W', 'X', 'U', 'X', r'$\Gamma$']

	pt = highsymm_path(np.array([gamma,X,W,K,gamma,L]),l) # make a path of all points
	pgp = np.array([0,4])*l[0]  # position of gamma points for ASR  Manually for the time being! ==> Just put index of where gamma points is in pt.
	plot_ticks = [r'$\Gamma$', 'X', 'W', 'K',r'$\Gamma$', 'L']


	nuq = pt.shape[0]  # Total number of all points
	print("number of q points=",nuq)


	# if load_previous_calculation==False:
	# 	if load_loaded_traj ==False:
	# 		# traj,Natoms,Nframes = read_xyz()
	# 		traj = np.load(folder_path+trajectory_file.split(".")[0]+'.npy')
	# 		Natoms = traj.shape[1]
	# 		Nframes = traj.shape[0]
	# 		# np.savez(folder_path+'temp_traj'+save_flag, traj=traj, Natoms=Natoms, Nframes=Nframes)
	# 	elif load_loaded_traj == True:
	# 		raise Exception("Disabled saving loaded trajectory.")
	# 		npz_file = np.load(folder_path+'temp_traj'+save_flag+'.npz')
	# 		traj =    npz_file['traj']
	# 		Natoms =  npz_file['Natoms']
	# 		Nframes = npz_file['Nframes']
	# 		print("file loaded!")

	# !!! new traj system
	traj = np.load(folder_path+trajectory_file.split(".")[0]+'.npy')
	Natoms = traj.shape[1]
	Nframes = traj.shape[0]
	# !!! end new traj system

	Natoms_root_rev = 1.0/np.sqrt(Natoms)
	# traj_for_FT = traj[0, :, 1:]
	traj =  traj[int(traj.shape[0]*skip_portion/100):,:,:]
	# traj_for_FT = np.mean(traj, axis=0)
	traj_for_FT = mean(traj)
	Nframes = traj.shape[0]

	# MAIN engine
	G_ft = greens_func(traj, traj_for_FT,pt)     # Calculates green function
	phi_ft = force_constants(G_ft)   # Calculates force matrix in reciprocal space
	phi_ft=ASR(phi_ft,pgp,nucell=1)            # Apply ASR
	freqs = eigenfreqs(phi_ft,nuq)   # Calculates eigen values which is frequencies
	print(" == FREQUENCIES (omega(q)) ==\n",freqs)

	# Save everything, if you wanted to change a little thing in plots
	np.save(folder_path+'temp_pt'+save_flag, pt)
	np.save(folder_path+'temp_freqs'+save_flag,freqs)

	# !!! disabling loading previous calc for the time being

	# elif load_previous_calculation==True:
	# 	pt= np.load(folder_path+'temp_pt'+save_flag+'.npy', allow_pickle=True)
	# 	freqs= np.load(folder_path+'temp_freqs'+save_flag+'.npy', allow_pickle=True)




	## project the path to 2D plot
	pt_diff =np.linalg.norm(np.diff(pt,axis=0),axis=1)
	# print pt_diff
	X=[0]
	plot_ticks_pos = [0]
	for ii in range(pt_diff.shape[0]):
		x=X[ii]+pt_diff[ii]
		X.append(x)
		if (ii+1)%3==0:
			plot_ticks_pos.append(x)

	print(freqs)
	plt.plot(X, freqs[:, 0]*1e-12,'o',color='black')
	plt.plot(X, freqs[:, 1]*1e-12,'o',color='black')
	plt.plot(X, freqs[:, 2]*1e-12,'o',color='black')
	# print(plot_ticks_pos,plot_ticks)
	plt.xticks(plot_ticks_pos,plot_ticks)
	plt.ylabel('THz')
	plt.savefig(folder_path+"test"+save_flag+".png")
	plt.show()





	return None

if __name__ == '__main__':
	main()