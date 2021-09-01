# -*- coding: utf-8 -*-
"""
Created on Mon May 13 2019

@author: iseyij
"""

from time import time
# import matlab.engine
import csv
from ..pySOT1 import *
from poap.controller import ThreadController, BasicWorkerThread
import numpy as np
import os.path
# import matplotlib.pyplot as plt
# from pylab import *
# from matplotlib import style
# import matplotlib.lines as  mlines
import modified_gp_regression as mgp
import modified_adaptive_sampling as mas
import os
from .gpr import GaussianProcessRegressor
from .kernels import (RBF, WhiteKernel, Matern, RationalQuadratic,
                     ExpSineSquared, DotProduct,
                     ConstantKernel as C)
from .gp_extras.kernels import ManifoldKernel
from .modified_test_problems import *
from .MFB import *
import modified_sot_sync_strategies as msss
from .generate_fixed_sample_points import Sample_points
import sys

from sklearn.cluster import KMeans, DBSCAN
from sklearn import metrics
from ..pySOT1.rbf import *
from ..pySOT1.experimental_design import SymmetricLatinHypercube, LatinHypercube
from multiprocessing import Process, pool
from .heuristic_methods import GeneticAlgorithm, MultimodalEDA
from scipy.spatial import distance
import seaborn as sns

from mpl_toolkits.mplot3d import Axes3D

from mpi4py import MPI


# %%%


def draw_graphs(data, X, Y, x_y_pair, fhat):
    def eval(x):
        return fhat.eval(x).ravel()

    fig = plt.figure()
    ax = fig.gca(projection='3d')
    x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))

    yy = np.zeros([x1.shape[0], x2.shape[0]])
    for i in range(x1.shape[0]):
        for k in range(x2.shape[0]):
            yy[i, k] = -data.objfunction_LF([x1[i], x2[k]])
    x1, x2 = np.meshgrid(x1, x2)
    ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
    plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))
    # ax.set_zticks([-150, -50, 50])
    x_points = np.zeros([len(x_y_pair), data.dim])
    y_values = np.zeros([len(x_y_pair)])
    for k in range(len(x_y_pair)):
        x_points[k, :] = x_y_pair[k]["point"]
        y_values[k] = x_y_pair[k]["value"]
    ax.scatter(-x_points[:, 0], -x_points[:, 1], -y_values[:], c='k', s=120)
    plt.show()
    # Save the plot into eps format
    script_dir = os.path.dirname(__file__)
    results_dir = os.path.join(script_dir, 'graphs_during_optimization/')
    # sample_file_name = function_name(i+1)+'.eps'
    # sample_file_name = function_name(i+1)+'.pdf'

    if not os.path.isdir(results_dir):
        os.makedirs(results_dir)

    # plt.savefig(results_dir + sample_file_name,dpi=1000,bbox_inches='tight')
    plt.savefig(results_dir + 'points_on_LF.eps', bbox_inches='tight')

    # draw HF function
    fig = plt.figure()
    ax = fig.gca(projection='3d')

    x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    for i in range(x1.shape[0]):
        for k in range(x2.shape[0]):
            yy[i, k] = -data.objfunction_HF([x1[i], x2[k]])
    x1, x2 = np.meshgrid(x1, x2)
    ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
    plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))
    # ax.set_zticks([-150, -50, 50])
    plt.show()
    plt.savefig(results_dir + 'HF_surface.eps', bbox_inches='tight')

    # draw LF with evaluated points
    fig = plt.figure()
    ax = fig.gca(projection='3d')

    x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    for i in range(x1.shape[0]):
        for k in range(x2.shape[0]):
            yy[i, k] = -data.objfunction_LF([x1[i], x2[k]])
    x1, x2 = np.meshgrid(x1, x2)
    ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
    plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))

    ax.scatter(-X[:, 0], -X[:, 1], -Y[:], c='k', s=120)
    plt.show()
    plt.savefig(results_dir + 'LF_surface.eps', bbox_inches='tight')

    if fhat != None:
        fig = plt.figure()
        ax = fig.gca(projection='3d')

        x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
        x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
        for i in range(x1.shape[0]):
            for k in range(x2.shape[0]):
                yy[i, k] = -eval([x1[i], x2[k]])
        x1, x2 = np.meshgrid(x1, x2)
        ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
        plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
        plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))

        ax.scatter(-x_points[:, 0], -x_points[:, 1], -y_values[:], c='k', s=120)
        plt.show()
        plt.savefig(results_dir + 'Surrogate_surface.eps', bbox_inches='tight')


def DYCORS_main(n_eval, model, maxeval, data, sampling_method, x_y_pair):
    start_time = time()
    # Define the essential parameters of PySOT
    nthreads = 1  # number of parallel threads / processes to be initiated (1 for serial)
    # maxeval = 50 # maximum number of function evaluations
    nsamples = nthreads  # number of simultaneous evaluations in each algorithm iteration (typically set equal to nthreads)

    #    n_eval = 2
    hisval = np.zeros([n_eval, maxeval])
    computation_cost = np.zeros([n_eval, 10])
    runtime = np.zeros([n_eval, 1])

    # Print setting of PySOT you are using (optional to remember what experimental options you used)
    # print("\nNumber of threads: " + str(nthreads))
    # print("Maximum number of evaluations: " + str(maxeval))
    # print("Search strategy: CandidateDYCORS")
    # print("Experimental design: Latin Hypercube")
    # print("Ensemble surrogates: "+str(model)+", domain scaled to unit box")

    ns = 2 * (data.dim + 1)

    # Create a strategy (defined in the pysot library) and a controller (defined in POAP library)

    for i in range(n_eval):
        t1 = time()
        # print('DYCORS: Start the ', str(i), 'th run:')
        controller = ThreadController()
        # This class instance manages the Parallel framework for assigning obj function evaluations to threads
        controller.strategy = \
            msss.SyncStrategyNoConstraints(
                worker_id=0, data=data,
                maxeval=maxeval, nsamples=nsamples,
                exp_design=LatinHypercube(dim=data.dim, npts=ns),
                response_surface=RSUnitbox(RBFInterpolant(kernel=model, maxp=maxeval), data),
                sampling_method=sampling_method,
                evaluated=x_y_pair

            )

        # Launch the threads and give them access to the objective function
        for _ in range(nthreads):
            worker = BasicWorkerThread(controller, data.objfunction)
            controller.launch_worker(worker)

        # Run the surrogate optimization strategy
        result = controller.run()
        t2 = time()
        runtime[i, 0] = (t2 - t1) - controller.strategy.Tmac

        # print('                 run time =',runtime[i,0])

        his_x_y = []
        hisval[i, 0] = controller.fevals[0].value
        his_x_y.append({"point": controller.fevals[0].params[0], "value": controller.fevals[0].value})
        for k in range(1, maxeval):
            his_x_y.append({"point": controller.fevals[k].params[0], "value": controller.fevals[k].value})
            if controller.fevals[k].value < hisval[i, k - 1]:
                hisval[i, k] = controller.fevals[k].value
            else:
                hisval[i, k] = hisval[i, k - 1]

        for s in range(10):
            computation_cost[i, s] = controller.strategy.iteration_cost[s]

    # print('Best value found: {0}'.format(result.value))
    # print('Best solution found: {0}\n'.format(np.array_str(result.params[0], max_line_width=np.inf,precision=5, suppress_small=True)))
    end_time = time()
    time_cost = np.sum(runtime) / n_eval
    # print('runtime = ', runtime)
    # print('time_cost = ', time_cost)
    # print('time of DYDCORS =', end_time - start_time)

    return result, hisval, time_cost, computation_cost, his_x_y
    # %%


def function_object(function_index, dim, eng):
    return {
        1: MFO_1(dim),
        2: MFO_2(dim),
        3: MFO_3(dim),
        4: MFO_4(dim),
        5: MFO_5(dim),
        6: MFO_6(dim),
        7: MFO_7(dim),
        8: MFO_8(dim),
        9: MFO_9(dim),
        10: MFO_10(dim),
        11: Styblinski_Tang(dim)
        # 12: Capacity_planning_1(dim, eng),
        # 13: Capacity_planning_2(dim, eng)
    }[function_index]


def function_name(function_index):
    return {
        1: 'MFO_1',
        2: 'MFO_2',
        3: 'MFO_3',
        4: 'MFO_4',
        5: 'MFO_5',
        6: 'MFO_6',
        7: 'MFO_7',
        8: 'MFO_8',
        9: 'MFO_9',
        10: 'MFO_10',
        11: 'Styblinski_Tang',
        12: 'Capacity_planning_1',
        13: 'Capacity_planning_2'
    }[function_index]


def multi_start_gradient(fhat, data, num_restart_, optimizer_id):
    def eval(x):
        return fhat.eval(x).ravel()

    def evals(x):
        return fhat.evals(x).ravel()

    def deriv(x):
        return fhat.deriv(x).ravel()

    num_restarts = max(5 * data.dim, num_restart_)
    new_points = np.zeros((num_restarts, data.dim))

    bounds = np.zeros((data.dim, 2))
    bounds[:, 0] = data.refine_xlow
    bounds[:, 1] = data.refine_xup

    # Generate start points using LHD sampling
    experiment_design = LatinHypercube(data.dim, num_restarts)
    start_points = experiment_design.generate_points()
    assert start_points.shape[1] == data.dim, \
        "Dimension mismatch between problem and experimental design"
    start_points = from_unit_box(start_points, data)

    # using Gradient based method
    if optimizer_id == 0:
        start_points = from_unit_box(start_points, data)
        fvals = np.zeros(num_restarts)
        xvals = np.zeros((num_restarts, data.dim))
        for i in range(num_restarts):
            x0 = start_points[i, :]
            res = minimize(eval, x0, method='L-BFGS-B', jac=deriv, bounds=bounds)

            # Compute the distance to the proposed points
            xx = np.atleast_2d(res.x)

            fvals[i] = res.fun
            xvals[i, :] = xx

    elif optimizer_id == 1:
        # using GA
        fvals = np.zeros(num_restarts)
        xvals = np.zeros((num_restarts, data.dim))
        for i in range(num_restarts):
            ga = GA(evals, data.dim, data.refine_xlow, data.refine_xup,
                    popsize=max([5 * data.dim, 20]), ngen=10 * data.dim, projfun=None, start="SLHD")
            x_min, f_min = ga.optimize()
            # GA's default setting is for minimization, min(-EI)

            fvals[i] = f_min
            xvals[i, :] = np.atleast_2d(x_min)
    else:
        eda = MultimodalEDA(eval, data.dim, data.refine_xlow, data.refine_xup,
                            popsize=100, ngen=2000, projfun=None, start="SLHD")
        x_min, f_min = eda.optimize()

        fvals = f_min
        xvals = x_min

    # using DBSCAN
    Labels = []
    N_clusters_ = []
    Metrics = []
    for ss in range(40):
        EPS = 0.005 * (ss + 1)
        db = DBSCAN(eps=EPS * distance.euclidean(data.xup, data.xlow), min_samples=1, metric='euclidean')
        y_pred = db.fit(xvals, fvals)
        Labels.append(db.labels_)
        N_clusters_.append(len(set(Labels[ss])) - (1 if -1 in Labels[ss] else 0))
        if N_clusters_[ss] >= 2 and N_clusters_[ss] <= 0.5 * max([5 * data.dim, 20]):
            Metrics.append(metrics.silhouette_score(xvals, Labels[ss], metric='sqeuclidean'))
        else:
            Metrics.append(-1)

    index_max = np.argmax(Metrics)
    labels = Labels[index_max]
    n_clusters_ = N_clusters_[index_max]
    # Nice Pythonic way to get the indices of the points for each corresponding cluster
    mydict = {i: np.where(labels == i)[0] for i in range(n_clusters_)}

    x_y_pair = []
    # Find the best point within each cluster
    for key, value in mydict.items():
        fb = fvals[value[0]]
        id = value[0]
        for item in value:
            if fb > fvals[item]:
                fb = fvals[item]
                id = item
        x_y_pair.append({"point": xvals[id, :], "value": fvals[id]})

    return x_y_pair


def data_mining(X, Y, data, method, optimizer_id):
    x_y_pair = []
    if method == 0:
        # using KMeans
        random_state = 100
        km = KMeans(n_clusters=data.dim, random_state=random_state)
        y_pred = km.fit_predict(X, Y)

        # Nice Pythonic way to get the indices of the points for each corresponding cluster
        mydict = {i: np.where(km.labels_ == i)[0] for i in range(km.n_clusters)}

        x_y_pair = []
        # Find the best point within each cluster
        for key, value in mydict.items():
            fb = Y[value[0]]
            id = value[0]
            for item in value:
                if fb > Y[item]:
                    fb = Y[item]
                    id = item
            x_y_pair.append({"point": X[id, :], "value": Y[id]})
    elif method == 1:
        # using DBSCAN
        Labels = []
        N_clusters_ = []
        Metrics = []
        for ss in range(40):
            EPS = 0.005 * (ss + 1)
            db = DBSCAN(eps=EPS * distance.euclidean(data.xup, data.xlow), min_samples=1, metric='euclidean')
            y_pred = db.fit(X, Y)
            Labels.append(db.labels_)
            N_clusters_.append(len(set(Labels[ss])) - (1 if -1 in Labels[ss] else 0))
            if N_clusters_[ss] >= 2:
                Metrics.append(metrics.silhouette_score(X, Labels[ss], metric='sqeuclidean'))
            else:
                Metrics.append(-1)

        index_max = np.argmax(Metrics)
        labels = Labels[index_max]
        n_clusters_ = N_clusters_[index_max]

        # Nice Pythonic way to get the indices of the points for each corresponding cluster
        mydict = {i: np.where(labels == i)[0] for i in range(n_clusters_)}

        x_y_pair = []
        # Find the best point within each cluster
        for key, value in mydict.items():
            fb = Y[value[0]]
            id = value[0]
            for item in value:
                if fb > Y[item]:
                    fb = Y[item]
                    id = item
            x_y_pair.append({"point": X[id, :], "value": Y[id]})

        for hh in range(len(Y)):
            print('error =', str(data.objfunction_LF(X[hh, :]) - Y[hh]))

        if data.dim == 2:
            fhat = None
            draw_graphs(data, X, Y, x_y_pair, fhat)

    elif method == 2:
        """
        using a multi-start gradient method to search on the surrogate from different start points for num_start_ times, and use a
        cluster algorithm to divide the local optima into N groups
        """

        fhat = RSUnitbox(RBFInterpolant(kernel=CubicKernel, maxp=X.shape[0]), data)

        # Find the nearest N points around current best point
        id = np.argmin(Y)
        dis = np.zeros([X.shape[0]])
        for k in range(X.shape[0]):
            dis[k] = distance.euclidean(X[k, :], X[id, :])
        rank_index = np.argsort(dis)

        x_tmp = np.zeros([int(0.5 * X.shape[0]), data.dim])
        for i in range(int(0.5 * X.shape[0])):
            x_tmp[i, :] = X[rank_index[i], :]
            fhat.add_point(X[rank_index[i], :], Y[rank_index[i]])

        data.refine_xlow = x_tmp.min(axis=0)
        data.refine_xup = x_tmp.max(axis=0)
        if data.dim > 10:
            num_restart_ = 100
        else:
            num_restart_ = 10 * data.dim

        x_y_pair_ = multi_start_gradient(fhat, data, num_restart_, optimizer_id)

        threshold = np.median(Y)

        for k, item in enumerate(x_y_pair_):
            # print('LF and surrogate error =', str(data.objfunction_LF(item["point"])-item["value"]))
            if data.objfunction_LF(item["point"]) < threshold:
                x_y_pair.append(x_y_pair_[k])

        # if data.dim == 2:
        #     draw_graphs(data, X, Y, x_y_pair, fhat)

        # if data.dim==2:
        # plt.figure(figsize=(12, 12))
        # fig=plt.subplot(221)
        # Make the plot
        # fig=plt.figure()
        # ax = fig.gca(projection='3d')
        # x1 = np.arange(data.xlow[0], data.xup[0], 0.005*(data.xup[0]-data.xlow[0]))
        # x2 = np.arange(data.xlow[0], data.xup[0], 0.005*(data.xup[0]-data.xlow[0]))
        #
        #
        # yy=np.zeros([x1.shape[0],x2.shape[0]])
        # for i in range(x1.shape[0]):
        #     for k in range(x2.shape[0]):
        #         yy[i,k] = -data.objfunction([x1[i],x2[k]])
        # x1, x2 = np.meshgrid(x1, x2)
        # ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm,linewidth=0, antialiased=False)
        # x_=np.zeros([len(x_y_pair),data.dim])
        # y_=np.zeros([len(x_y_pair)])
        # for k,item in enumerate(x_y_pair):
        #     x_[k,:]=item['point']
        #     y_[k]=-data.objfunction(x_[k,:])
        # ax.scatter(x_[:,0], x_[:,1], y_[:], c='k', s=60)
        # plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
        # plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))
        # ax.set_zticks([-150, -50, 50])
        # plt.show()
        #
        #     # to Add a color bar which maps values to colors.
        #
        #
        #     plt.title("Incorrect Number of Blobs")

    return x_y_pair


def main(dim, mfo_method_index, data_mining_index, run_index, p, optimizer_id, fun_index):
    pst = time()

    runs = 1
    # print('Current run index=:', str(run_index))
    method_type = 'CRBF_Restart'
    maxeval = 15 * dim + 350
    # maxeval = 10*dim
    R = 10

    maxeval_l = np.int(p * maxeval * R)
    maxeval_h = maxeval - np.int(p * maxeval)

    # eng = matlab.engine.start_matlab()
    eng = []

    i = fun_index

    data = function_object(i + 1, dim, eng)

    # print(data.info)
    sampling_method = mas.CandidateDYCORS(data=data, numcand=100 * data.dim)

    if mfo_method_index == 0:
        mfo_method = 'MFO_RBF_DYCORS_basic'
        data_mining_method = 'None'
        optimizer = 'None'
        # Run on the LF model
        data.objfunction = data.objfunction_LF
        data.search_type = 'exploration'
        # print("Start the run on LF model")
        x_y_pair = []
        [result_l, hisval_l, time_cost_l, computation_cost_l, his_x_y_l] = DYCORS_main(runs, CubicKernel, maxeval_l,
                                                                                       data, sampling_method, x_y_pair)

        # move to step 2- select the best point in the LF run
        x_y_pair = []
        x_y_pair.append({"point": result_l.params[0], "value": result_l.value})

        # Run on the HF model
        # print("Start the run on HF model")
        data.objfunction = data.objfunction_HF
        data.search_type = 'exploitation'
        [result_h, hisval_h, time_cost_h, computation_cost_h, his_x_y_h] = DYCORS_main(runs, CubicKernel, maxeval_h,
                                                                                       data, sampling_method, x_y_pair)
    elif mfo_method_index == 1:
        mfo_method = 'MFO_RBF_DYCORS_improved'
        # Run on the LF model
        data.objfunction = data.objfunction_LF
        data.search_type = 'exploration'
        # print("Start the run on LF model")
        x_y_pair = []
        [result_l, hisval_l, time_cost_l, computation_cost_l, his_x_y_l] = DYCORS_main(runs, CubicKernel, maxeval_l,
                                                                                       data, sampling_method,
                                                                                       x_y_pair)

        # move to step 2- select the best N point in the LF run by using data mining method
        X = np.zeros([maxeval_l, data.dim])
        Y = np.zeros([maxeval_l])
        for k, item in enumerate(his_x_y_l):
            X[k, :] = item["point"]
            Y[k] = item["value"]

        # Begin the data mining stage!
        x_y_pair_ = data_mining(X, Y, data, data_mining_index, optimizer_id)
        if data_mining_index == 0:
            data_mining_method = 'KMeans'
        elif data_mining_index == 1:
            data_mining_method = 'DBSCAN'
        elif data_mining_index == 2:
            data_mining_method = 'Multi_Restart_Gradient'

        if optimizer_id == 0:
            optimizer = 'BFGS'
        elif optimizer_id == 1:
            optimizer = 'GA'
        elif optimizer_id == 2:
            optimizer = 'MEDA'

        # if data.dim==2:
        #     plt.figure(figsize=(12, 12))
        #     plt.subplot(221)
        #     plt.scatter(X[:, 0], X[:, 1], c=y_pred)
        #     plt.title("Incorrect Number of Blobs")

        x_y_pair.append({"point": result_l.params[0], "value": result_l.value})
        for ss in range(len(x_y_pair_)):
            x_y_pair.append(x_y_pair_[ss])
        # Run on the HF model
        # print("Start the run on HF model")
        data.objfunction = data.objfunction_HF
        data.search_type = 'exploitation'
        # for k in range(len(x_y_pair)):
        #     print('points =', str(x_y_pair[k]["point"]), 'value = ', str(x_y_pair[k]["value"]))
        [result_h, hisval_h, time_cost_h, computation_cost_h, his_x_y_h] = DYCORS_main(runs, CubicKernel, maxeval_h,
                                                                                       data, sampling_method,
                                                                                       x_y_pair)

    hisY = np.zeros(maxeval)
    for k in range(maxeval):
        if k < (maxeval - maxeval_h):
            hisY[k] = np.inf
        else:
            hisY[k] = hisval_h[0, k - (maxeval - maxeval_h)]

    totalT = time() - pst

    filename1 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name1 = 'time_cost' + '.csv'
    script_dir1 = os.path.dirname(__file__)
    results_dir1 = os.path.join(script_dir1, filename1)
    if not os.path.isdir(results_dir1):
        os.makedirs(results_dir1)
    filehead1 = ['', '', mfo_method, 'LF', 'HF', 'total']
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir1 + sample_file_name1, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir1 + sample_file_name1, 'wb')

    writer = csv.writer(a)
    writer.writerow(filehead1)
    a.close()
    s = 'F' + str(i + 1)
    t = [s, '', '', str(time_cost_l), str(time_cost_h), str(totalT)]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile1 = open(results_dir1 + sample_file_name1, 'a', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile1 = open(results_dir1 + sample_file_name1, 'ab')

    writer = csv.writer(csvfile1)
    writer.writerow(t)
    csvfile1.close()

    filename5 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name5 = 'history_x_y_l' + '.csv'
    script_dir5 = os.path.dirname(__file__)
    results_dir5 = os.path.join(script_dir5, filename5)
    if not os.path.isdir(results_dir5):
        os.makedirs(results_dir5)
    filehead5 = ['', '', mfo_method]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir5 + sample_file_name5, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir5 + sample_file_name5, 'wb')

    writer = csv.writer(a)
    writer.writerow(filehead5)
    a.close()
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile5 = open(results_dir5 + sample_file_name5, 'a', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile5 = open(results_dir5 + sample_file_name5, 'ab')
    writer = csv.writer(csvfile5)
    writer.writerow([s])
    for k, item in enumerate(his_x_y_l):
        tmp = [str(k + 1), '']
        for h in range(data.dim):
            tmp.append(str(item["point"][h]))
        tmp.append(str(item["value"]))
        writer.writerow(tmp)
    csvfile5.close()

    filename6 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(
        maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name6 = 'history_x_y_h' + '.csv'
    script_dir6 = os.path.dirname(__file__)
    results_dir6 = os.path.join(script_dir6, filename6)
    if not os.path.isdir(results_dir6):
        os.makedirs(results_dir6)
    filehead6 = ['', '', mfo_method]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir6 + sample_file_name6, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir6 + sample_file_name6, 'wb')
    writer = csv.writer(a)
    writer.writerow(filehead6)
    a.close()
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile6 = open(results_dir6 + sample_file_name6, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile6 = open(results_dir6 + sample_file_name6, 'wb')

    writer = csv.writer(csvfile6)
    writer.writerow([s])
    for k, item in enumerate(his_x_y_h):
        tmp = [str(k + 1), '']
        for h in range(data.dim):
            tmp.append(str(item["point"][h]))
        tmp.append(str(item["value"]))
        writer.writerow(tmp)
    csvfile6.close()

    filename7 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(
        maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name7 = 'Average_convergence_history' + '.csv'
    script_dir7 = os.path.dirname(__file__)
    results_dir7 = os.path.join(script_dir7, filename7)
    if not os.path.isdir(results_dir7):
        os.makedirs(results_dir7)
    filehead7 = ['', '', mfo_method]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir7 + sample_file_name7, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir7 + sample_file_name7, 'wb')
    writer = csv.writer(a)
    writer.writerow(filehead7)
    a.close()
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile7 = open(results_dir7 + sample_file_name7, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile7 = open(results_dir7 + sample_file_name7, 'wb')
    writer = csv.writer(csvfile7)
    writer.writerow([s])
    for k in range(maxeval):
        writer.writerow(['', str(k + 1), str(hisY[k])])
    csvfile7.close()

    print(optimizer, ', p=' + str(p), 'F' + str(i + 1), ', ', str(dim) + '-d, ',
          str(run_index + 1), 'th run has been finished!!!')


# -*- coding: utf-8 -*-
"""
Created on Mon May 13 2019

@author: iseyij
"""

from time import time
# import matlab.engine
import csv
from pySOT import *
from poap.controller import ThreadController, BasicWorkerThread
import numpy as np
import os.path
# import matplotlib.pyplot as plt
# from pylab import *
# from matplotlib import style
# import matplotlib.lines as  mlines
import modified_gp_regression as mgp
import modified_adaptive_sampling as mas
import os
from gpr import GaussianProcessRegressor
from kernels import (RBF, WhiteKernel, Matern, RationalQuadratic,
                     ExpSineSquared, DotProduct,
                     ConstantKernel as C)
from gp_extras.kernels import ManifoldKernel
from modified_test_problems import *
from MFB import *
import modified_sot_sync_strategies as msss
from generate_fixed_sample_points import Sample_points
import sys

from sklearn.cluster import KMeans, DBSCAN
from sklearn import metrics
from pySOT.rbf import *
from pySOT.experimental_design import SymmetricLatinHypercube, LatinHypercube
from multiprocessing import Process, pool
from heuristic_methods import GeneticAlgorithm, MultimodalEDA
from scipy.spatial import distance
import seaborn as sns

from mpl_toolkits.mplot3d import Axes3D

from mpi4py import MPI


# %%%


def draw_graphs(data, X, Y, x_y_pair, fhat):
    def eval(x):
        return fhat.eval(x).ravel()

    fig = plt.figure()
    ax = fig.gca(projection='3d')
    x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))

    yy = np.zeros([x1.shape[0], x2.shape[0]])
    for i in range(x1.shape[0]):
        for k in range(x2.shape[0]):
            yy[i, k] = -data.objfunction_LF([x1[i], x2[k]])
    x1, x2 = np.meshgrid(x1, x2)
    ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
    plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))
    # ax.set_zticks([-150, -50, 50])
    x_points = np.zeros([len(x_y_pair), data.dim])
    y_values = np.zeros([len(x_y_pair)])
    for k in range(len(x_y_pair)):
        x_points[k, :] = x_y_pair[k]["point"]
        y_values[k] = x_y_pair[k]["value"]
    ax.scatter(-x_points[:, 0], -x_points[:, 1], -y_values[:], c='k', s=120)
    plt.show()
    # Save the plot into eps format
    script_dir = os.path.dirname(__file__)
    results_dir = os.path.join(script_dir, 'graphs_during_optimization/')
    # sample_file_name = function_name(i+1)+'.eps'
    # sample_file_name = function_name(i+1)+'.pdf'

    if not os.path.isdir(results_dir):
        os.makedirs(results_dir)

    # plt.savefig(results_dir + sample_file_name,dpi=1000,bbox_inches='tight')
    plt.savefig(results_dir + 'points_on_LF.eps', bbox_inches='tight')

    # draw HF function
    fig = plt.figure()
    ax = fig.gca(projection='3d')

    x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    for i in range(x1.shape[0]):
        for k in range(x2.shape[0]):
            yy[i, k] = -data.objfunction_HF([x1[i], x2[k]])
    x1, x2 = np.meshgrid(x1, x2)
    ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
    plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))
    # ax.set_zticks([-150, -50, 50])
    plt.show()
    plt.savefig(results_dir + 'HF_surface.eps', bbox_inches='tight')

    # draw LF with evaluated points
    fig = plt.figure()
    ax = fig.gca(projection='3d')

    x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
    for i in range(x1.shape[0]):
        for k in range(x2.shape[0]):
            yy[i, k] = -data.objfunction_LF([x1[i], x2[k]])
    x1, x2 = np.meshgrid(x1, x2)
    ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
    plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))

    ax.scatter(-X[:, 0], -X[:, 1], -Y[:], c='k', s=120)
    plt.show()
    plt.savefig(results_dir + 'LF_surface.eps', bbox_inches='tight')

    if fhat != None:
        fig = plt.figure()
        ax = fig.gca(projection='3d')

        x1 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
        x2 = np.arange(data.xlow[0], data.xup[0], 0.005 * (data.xup[0] - data.xlow[0]))
        for i in range(x1.shape[0]):
            for k in range(x2.shape[0]):
                yy[i, k] = -eval([x1[i], x2[k]])
        x1, x2 = np.meshgrid(x1, x2)
        ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm, linewidth=0, antialiased=False)
        plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
        plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))

        ax.scatter(-x_points[:, 0], -x_points[:, 1], -y_values[:], c='k', s=120)
        plt.show()
        plt.savefig(results_dir + 'Surrogate_surface.eps', bbox_inches='tight')


def DYCORS_main(n_eval, model, maxeval, data, sampling_method, x_y_pair):
    start_time = time()
    # Define the essential parameters of PySOT
    nthreads = 1  # number of parallel threads / processes to be initiated (1 for serial)
    # maxeval = 50 # maximum number of function evaluations
    nsamples = nthreads  # number of simultaneous evaluations in each algorithm iteration (typically set equal to nthreads)

    #    n_eval = 2
    hisval = np.zeros([n_eval, maxeval])
    computation_cost = np.zeros([n_eval, 10])
    runtime = np.zeros([n_eval, 1])

    # Print setting of PySOT you are using (optional to remember what experimental options you used)
    # print("\nNumber of threads: " + str(nthreads))
    # print("Maximum number of evaluations: " + str(maxeval))
    # print("Search strategy: CandidateDYCORS")
    # print("Experimental design: Latin Hypercube")
    # print("Ensemble surrogates: "+str(model)+", domain scaled to unit box")

    ns = 2 * (data.dim + 1)

    # Create a strategy (defined in the pysot library) and a controller (defined in POAP library)

    for i in range(n_eval):
        t1 = time()
        # print('DYCORS: Start the ', str(i), 'th run:')
        controller = ThreadController()
        # This class instance manages the Parallel framework for assigning obj function evaluations to threads
        controller.strategy = \
            msss.SyncStrategyNoConstraints(
                worker_id=0, data=data,
                maxeval=maxeval, nsamples=nsamples,
                exp_design=LatinHypercube(dim=data.dim, npts=ns),
                response_surface=RSUnitbox(RBFInterpolant(kernel=model, maxp=maxeval), data),
                sampling_method=sampling_method,
                evaluated=x_y_pair

            )

        # Launch the threads and give them access to the objective function
        for _ in range(nthreads):
            worker = BasicWorkerThread(controller, data.objfunction)
            controller.launch_worker(worker)

        # Run the surrogate optimization strategy
        result = controller.run()
        t2 = time()
        runtime[i, 0] = (t2 - t1) - controller.strategy.Tmac

        # print('                 run time =',runtime[i,0])

        his_x_y = []
        hisval[i, 0] = controller.fevals[0].value
        his_x_y.append({"point": controller.fevals[0].params[0], "value": controller.fevals[0].value})
        for k in range(1, maxeval):
            his_x_y.append({"point": controller.fevals[k].params[0], "value": controller.fevals[k].value})
            if controller.fevals[k].value < hisval[i, k - 1]:
                hisval[i, k] = controller.fevals[k].value
            else:
                hisval[i, k] = hisval[i, k - 1]

        for s in range(10):
            computation_cost[i, s] = controller.strategy.iteration_cost[s]

    # print('Best value found: {0}'.format(result.value))
    # print('Best solution found: {0}\n'.format(np.array_str(result.params[0], max_line_width=np.inf,precision=5, suppress_small=True)))
    end_time = time()
    time_cost = np.sum(runtime) / n_eval
    # print('runtime = ', runtime)
    # print('time_cost = ', time_cost)
    # print('time of DYDCORS =', end_time - start_time)

    return result, hisval, time_cost, computation_cost, his_x_y
    # %%


def function_object(function_index, dim, eng):
    return {
        1: MFO_1(dim),
        2: MFO_2(dim),
        3: MFO_3(dim),
        4: MFO_4(dim),
        5: MFO_5(dim),
        6: MFO_6(dim),
        7: MFO_7(dim),
        8: MFO_8(dim),
        9: MFO_9(dim),
        10: MFO_10(dim),
        11: Styblinski_Tang(dim)
        # 12: Capacity_planning_1(dim, eng),
        # 13: Capacity_planning_2(dim, eng)
    }[function_index]


def function_name(function_index):
    return {
        1: 'MFO_1',
        2: 'MFO_2',
        3: 'MFO_3',
        4: 'MFO_4',
        5: 'MFO_5',
        6: 'MFO_6',
        7: 'MFO_7',
        8: 'MFO_8',
        9: 'MFO_9',
        10: 'MFO_10',
        11: 'Styblinski_Tang',
        12: 'Capacity_planning_1',
        13: 'Capacity_planning_2'
    }[function_index]


def multi_start_gradient(fhat, data, num_restart_, optimizer_id):
    def eval(x):
        return fhat.eval(x).ravel()

    def evals(x):
        return fhat.evals(x).ravel()

    def deriv(x):
        return fhat.deriv(x).ravel()

    num_restarts = max(5 * data.dim, num_restart_)
    new_points = np.zeros((num_restarts, data.dim))

    bounds = np.zeros((data.dim, 2))
    bounds[:, 0] = data.refine_xlow
    bounds[:, 1] = data.refine_xup

    # Generate start points using LHD sampling
    experiment_design = LatinHypercube(data.dim, num_restarts)
    start_points = experiment_design.generate_points()
    assert start_points.shape[1] == data.dim, \
        "Dimension mismatch between problem and experimental design"
    start_points = from_unit_box(start_points, data)

    # using Gradient based method
    if optimizer_id == 0:
        start_points = from_unit_box(start_points, data)
        fvals = np.zeros(num_restarts)
        xvals = np.zeros((num_restarts, data.dim))
        for i in range(num_restarts):
            x0 = start_points[i, :]
            res = minimize(eval, x0, method='L-BFGS-B', jac=deriv, bounds=bounds)

            # Compute the distance to the proposed points
            xx = np.atleast_2d(res.x)

            fvals[i] = res.fun
            xvals[i, :] = xx

    elif optimizer_id == 1:
        # using GA
        fvals = np.zeros(num_restarts)
        xvals = np.zeros((num_restarts, data.dim))
        for i in range(num_restarts):
            ga = GA(evals, data.dim, data.refine_xlow, data.refine_xup,
                    popsize=max([5 * data.dim, 20]), ngen=10 * data.dim, projfun=None, start="SLHD")
            x_min, f_min = ga.optimize()
            # GA's default setting is for minimization, min(-EI)

            fvals[i] = f_min
            xvals[i, :] = np.atleast_2d(x_min)
    else:
        eda = MultimodalEDA(eval, data.dim, data.refine_xlow, data.refine_xup,
                            popsize=100, ngen=2000, projfun=None, start="SLHD")
        x_min, f_min = eda.optimize()

        fvals = f_min
        xvals = x_min

    # using DBSCAN
    Labels = []
    N_clusters_ = []
    Metrics = []
    for ss in range(40):
        EPS = 0.005 * (ss + 1)
        db = DBSCAN(eps=EPS * distance.euclidean(data.xup, data.xlow), min_samples=1, metric='euclidean')
        y_pred = db.fit(xvals, fvals)
        Labels.append(db.labels_)
        N_clusters_.append(len(set(Labels[ss])) - (1 if -1 in Labels[ss] else 0))
        if N_clusters_[ss] >= 2 and N_clusters_[ss] <= 0.5 * max([5 * data.dim, 20]):
            Metrics.append(metrics.silhouette_score(xvals, Labels[ss], metric='sqeuclidean'))
        else:
            Metrics.append(-1)

    index_max = np.argmax(Metrics)
    labels = Labels[index_max]
    n_clusters_ = N_clusters_[index_max]
    # Nice Pythonic way to get the indices of the points for each corresponding cluster
    mydict = {i: np.where(labels == i)[0] for i in range(n_clusters_)}

    x_y_pair = []
    # Find the best point within each cluster
    for key, value in mydict.items():
        fb = fvals[value[0]]
        id = value[0]
        for item in value:
            if fb > fvals[item]:
                fb = fvals[item]
                id = item
        x_y_pair.append({"point": xvals[id, :], "value": fvals[id]})

    return x_y_pair


def data_mining(X, Y, data, method, optimizer_id):
    x_y_pair = []
    if method == 0:
        # using KMeans
        random_state = 100
        km = KMeans(n_clusters=data.dim, random_state=random_state)
        y_pred = km.fit_predict(X, Y)

        # Nice Pythonic way to get the indices of the points for each corresponding cluster
        mydict = {i: np.where(km.labels_ == i)[0] for i in range(km.n_clusters)}

        x_y_pair = []
        # Find the best point within each cluster
        for key, value in mydict.items():
            fb = Y[value[0]]
            id = value[0]
            for item in value:
                if fb > Y[item]:
                    fb = Y[item]
                    id = item
            x_y_pair.append({"point": X[id, :], "value": Y[id]})
    elif method == 1:
        # using DBSCAN
        Labels = []
        N_clusters_ = []
        Metrics = []
        for ss in range(40):
            EPS = 0.005 * (ss + 1)
            db = DBSCAN(eps=EPS * distance.euclidean(data.xup, data.xlow), min_samples=1, metric='euclidean')
            y_pred = db.fit(X, Y)
            Labels.append(db.labels_)
            N_clusters_.append(len(set(Labels[ss])) - (1 if -1 in Labels[ss] else 0))
            if N_clusters_[ss] >= 2:
                Metrics.append(metrics.silhouette_score(X, Labels[ss], metric='sqeuclidean'))
            else:
                Metrics.append(-1)

        index_max = np.argmax(Metrics)
        labels = Labels[index_max]
        n_clusters_ = N_clusters_[index_max]

        # Nice Pythonic way to get the indices of the points for each corresponding cluster
        mydict = {i: np.where(labels == i)[0] for i in range(n_clusters_)}

        x_y_pair = []
        # Find the best point within each cluster
        for key, value in mydict.items():
            fb = Y[value[0]]
            id = value[0]
            for item in value:
                if fb > Y[item]:
                    fb = Y[item]
                    id = item
            x_y_pair.append({"point": X[id, :], "value": Y[id]})

        for hh in range(len(Y)):
            print('error =', str(data.objfunction_LF(X[hh, :]) - Y[hh]))

        if data.dim == 2:
            fhat = None
            draw_graphs(data, X, Y, x_y_pair, fhat)

    elif method == 2:
        """
        using a multi-start gradient method to search on the surrogate from different start points for num_start_ times, and use a
        cluster algorithm to divide the local optima into N groups
        """

        fhat = RSUnitbox(RBFInterpolant(kernel=CubicKernel, maxp=X.shape[0]), data)

        # Find the nearest N points around current best point
        id = np.argmin(Y)
        dis = np.zeros([X.shape[0]])
        for k in range(X.shape[0]):
            dis[k] = distance.euclidean(X[k, :], X[id, :])
        rank_index = np.argsort(dis)

        x_tmp = np.zeros([int(0.5 * X.shape[0]), data.dim])
        for i in range(int(0.5 * X.shape[0])):
            x_tmp[i, :] = X[rank_index[i], :]
            fhat.add_point(X[rank_index[i], :], Y[rank_index[i]])

        data.refine_xlow = x_tmp.min(axis=0)
        data.refine_xup = x_tmp.max(axis=0)
        if data.dim > 10:
            num_restart_ = 100
        else:
            num_restart_ = 10 * data.dim

        x_y_pair_ = multi_start_gradient(fhat, data, num_restart_, optimizer_id)

        threshold = np.median(Y)

        for k, item in enumerate(x_y_pair_):
            # print('LF and surrogate error =', str(data.objfunction_LF(item["point"])-item["value"]))
            if data.objfunction_LF(item["point"]) < threshold:
                x_y_pair.append(x_y_pair_[k])

        # if data.dim == 2:
        #     draw_graphs(data, X, Y, x_y_pair, fhat)

        # if data.dim==2:
        # plt.figure(figsize=(12, 12))
        # fig=plt.subplot(221)
        # Make the plot
        # fig=plt.figure()
        # ax = fig.gca(projection='3d')
        # x1 = np.arange(data.xlow[0], data.xup[0], 0.005*(data.xup[0]-data.xlow[0]))
        # x2 = np.arange(data.xlow[0], data.xup[0], 0.005*(data.xup[0]-data.xlow[0]))
        #
        #
        # yy=np.zeros([x1.shape[0],x2.shape[0]])
        # for i in range(x1.shape[0]):
        #     for k in range(x2.shape[0]):
        #         yy[i,k] = -data.objfunction([x1[i],x2[k]])
        # x1, x2 = np.meshgrid(x1, x2)
        # ax.plot_surface(x1, x2, yy, cmap=cm.coolwarm,linewidth=0, antialiased=False)
        # x_=np.zeros([len(x_y_pair),data.dim])
        # y_=np.zeros([len(x_y_pair)])
        # for k,item in enumerate(x_y_pair):
        #     x_[k,:]=item['point']
        #     y_[k]=-data.objfunction(x_[k,:])
        # ax.scatter(x_[:,0], x_[:,1], y_[:], c='k', s=60)
        # plt.xticks(np.arange(data.xlow[0], data.xup[0], 0.5))
        # plt.yticks(np.arange(data.xlow[1], data.xup[1], 0.5))
        # ax.set_zticks([-150, -50, 50])
        # plt.show()
        #
        #     # to Add a color bar which maps values to colors.
        #
        #
        #     plt.title("Incorrect Number of Blobs")

    return x_y_pair


def main(dim, mfo_method_index, data_mining_index, run_index, p, optimizer_id, fun_index):
    pst = time()

    runs = 1
    # print('Current run index=:', str(run_index))
    method_type = 'CRBF_Restart'
    maxeval = 15 * dim + 350
    # maxeval = 10*dim
    R = 10

    maxeval_l = np.int(p * maxeval * R)
    maxeval_h = maxeval - np.int(p * maxeval)

    # eng = matlab.engine.start_matlab()
    eng = []

    i = fun_index

    data = function_object(i + 1, dim, eng)

    # print(data.info)
    sampling_method = mas.CandidateDYCORS(data=data, numcand=100 * data.dim)

    if mfo_method_index == 0:
        mfo_method = 'MFO_RBF_DYCORS_basic'
        data_mining_method = 'None'
        optimizer = 'None'
        # Run on the LF model
        data.objfunction = data.objfunction_LF
        data.search_type = 'exploration'
        # print("Start the run on LF model")
        x_y_pair = []
        [result_l, hisval_l, time_cost_l, computation_cost_l, his_x_y_l] = DYCORS_main(runs, CubicKernel, maxeval_l,
                                                                                       data, sampling_method, x_y_pair)

        # move to step 2- select the best point in the LF run
        x_y_pair = []
        x_y_pair.append({"point": result_l.params[0], "value": result_l.value})

        # Run on the HF model
        # print("Start the run on HF model")
        data.objfunction = data.objfunction_HF
        data.search_type = 'exploitation'
        [result_h, hisval_h, time_cost_h, computation_cost_h, his_x_y_h] = DYCORS_main(runs, CubicKernel, maxeval_h,
                                                                                       data, sampling_method, x_y_pair)
    elif mfo_method_index == 1:
        mfo_method = 'MFO_RBF_DYCORS_improved'
        # Run on the LF model
        data.objfunction = data.objfunction_LF
        data.search_type = 'exploration'
        # print("Start the run on LF model")
        x_y_pair = []
        [result_l, hisval_l, time_cost_l, computation_cost_l, his_x_y_l] = DYCORS_main(runs, CubicKernel, maxeval_l,
                                                                                       data, sampling_method,
                                                                                       x_y_pair)

        # move to step 2- select the best N point in the LF run by using data mining method
        X = np.zeros([maxeval_l, data.dim])
        Y = np.zeros([maxeval_l])
        for k, item in enumerate(his_x_y_l):
            X[k, :] = item["point"]
            Y[k] = item["value"]

        # Begin the data mining stage!
        x_y_pair_ = data_mining(X, Y, data, data_mining_index, optimizer_id)
        if data_mining_index == 0:
            data_mining_method = 'KMeans'
        elif data_mining_index == 1:
            data_mining_method = 'DBSCAN'
        elif data_mining_index == 2:
            data_mining_method = 'Multi_Restart_Gradient'

        if optimizer_id == 0:
            optimizer = 'BFGS'
        elif optimizer_id == 1:
            optimizer = 'GA'
        elif optimizer_id == 2:
            optimizer = 'MEDA'

        # if data.dim==2:
        #     plt.figure(figsize=(12, 12))
        #     plt.subplot(221)
        #     plt.scatter(X[:, 0], X[:, 1], c=y_pred)
        #     plt.title("Incorrect Number of Blobs")

        x_y_pair.append({"point": result_l.params[0], "value": result_l.value})
        for ss in range(len(x_y_pair_)):
            x_y_pair.append(x_y_pair_[ss])
        # Run on the HF model
        # print("Start the run on HF model")
        data.objfunction = data.objfunction_HF
        data.search_type = 'exploitation'
        # for k in range(len(x_y_pair)):
        #     print('points =', str(x_y_pair[k]["point"]), 'value = ', str(x_y_pair[k]["value"]))
        [result_h, hisval_h, time_cost_h, computation_cost_h, his_x_y_h] = DYCORS_main(runs, CubicKernel, maxeval_h,
                                                                                       data, sampling_method,
                                                                                       x_y_pair)

    hisY = np.zeros(maxeval)
    for k in range(maxeval):
        if k < (maxeval - maxeval_h):
            hisY[k] = np.inf
        else:
            hisY[k] = hisval_h[0, k - (maxeval - maxeval_h)]

    totalT = time() - pst

    filename1 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name1 = 'time_cost' + '.csv'
    script_dir1 = os.path.dirname(__file__)
    results_dir1 = os.path.join(script_dir1, filename1)
    if not os.path.isdir(results_dir1):
        os.makedirs(results_dir1)
    filehead1 = ['', '', mfo_method, 'LF', 'HF', 'total']
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir1 + sample_file_name1, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir1 + sample_file_name1, 'wb')

    writer = csv.writer(a)
    writer.writerow(filehead1)
    a.close()
    s = 'F' + str(i + 1)
    t = [s, '', '', str(time_cost_l), str(time_cost_h), str(totalT)]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile1 = open(results_dir1 + sample_file_name1, 'a', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile1 = open(results_dir1 + sample_file_name1, 'ab')

    writer = csv.writer(csvfile1)
    writer.writerow(t)
    csvfile1.close()

    filename5 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name5 = 'history_x_y_l' + '.csv'
    script_dir5 = os.path.dirname(__file__)
    results_dir5 = os.path.join(script_dir5, filename5)
    if not os.path.isdir(results_dir5):
        os.makedirs(results_dir5)
    filehead5 = ['', '', mfo_method]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir5 + sample_file_name5, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir5 + sample_file_name5, 'wb')

    writer = csv.writer(a)
    writer.writerow(filehead5)
    a.close()
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile5 = open(results_dir5 + sample_file_name5, 'a', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile5 = open(results_dir5 + sample_file_name5, 'ab')
    writer = csv.writer(csvfile5)
    writer.writerow([s])
    for k, item in enumerate(his_x_y_l):
        tmp = [str(k + 1), '']
        for h in range(data.dim):
            tmp.append(str(item["point"][h]))
        tmp.append(str(item["value"]))
        writer.writerow(tmp)
    csvfile5.close()

    filename6 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(
        maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name6 = 'history_x_y_h' + '.csv'
    script_dir6 = os.path.dirname(__file__)
    results_dir6 = os.path.join(script_dir6, filename6)
    if not os.path.isdir(results_dir6):
        os.makedirs(results_dir6)
    filehead6 = ['', '', mfo_method]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir6 + sample_file_name6, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir6 + sample_file_name6, 'wb')
    writer = csv.writer(a)
    writer.writerow(filehead6)
    a.close()
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile6 = open(results_dir6 + sample_file_name6, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile6 = open(results_dir6 + sample_file_name6, 'wb')

    writer = csv.writer(csvfile6)
    writer.writerow([s])
    for k, item in enumerate(his_x_y_h):
        tmp = [str(k + 1), '']
        for h in range(data.dim):
            tmp.append(str(item["point"][h]))
        tmp.append(str(item["value"]))
        writer.writerow(tmp)
    csvfile6.close()

    filename7 = 'Result_Record/MFO/' + mfo_method + '/' + data_mining_method + '/' + optimizer + '/' + 'p=' + str(
        p) + '/' + 'F' + str(i + 1) + '/' + str(dim) + 'dim/' + str(
        maxeval) + 'maxeval/' + str(run_index + 1) + '/'
    sample_file_name7 = 'Average_convergence_history' + '.csv'
    script_dir7 = os.path.dirname(__file__)
    results_dir7 = os.path.join(script_dir7, filename7)
    if not os.path.isdir(results_dir7):
        os.makedirs(results_dir7)
    filehead7 = ['', '', mfo_method]
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        a = open(results_dir7 + sample_file_name7, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        a = open(results_dir7 + sample_file_name7, 'wb')
    writer = csv.writer(a)
    writer.writerow(filehead7)
    a.close()
    if (sys.version_info > (3, 0)):
        # Python 3 code in this block
        csvfile7 = open(results_dir7 + sample_file_name7, 'w', encoding='utf8', newline='')
    else:
        # Python 2 code in this block
        csvfile7 = open(results_dir7 + sample_file_name7, 'wb')
    writer = csv.writer(csvfile7)
    writer.writerow([s])
    for k in range(maxeval):
        writer.writerow(['', str(k + 1), str(hisY[k])])
    csvfile7.close()

    print(optimizer, ', p=' + str(p), 'F' + str(i + 1), ', ', str(dim) + '-d, ',
          str(run_index + 1), 'th run has been finished!!!')


def run_main(a, dim):
    for p in range(8, 9):
        for optimizer in range(1, 3):
            for run_index in range(10 * a, 10 * a + 10):
                for fun_index in range(5, 10):
                    print('dim=', str(dim), ' optimizer=', str(optimizer), ' fun_index=', str(fun_index), ' run_index=',
                          str(run_index))
                    main(dim, 1, 2, run_index, 0.1 * p, optimizer, fun_index)


if __name__ == "__main__":

    # print('**********program starts!!!************')
    # comm = MPI.COMM_WORLD
    # rank = comm.Get_rank()
    # run_num = 3
    # #
    # #
    # #
    # a = rank%run_num
    # id = int(rank/run_num)%2
    # fun_index = int(rank/(2*run_num))
    # dim = [10, 30]
    # print("a, rank = ", str(a), str(rank))
    procs = []

    for s in range(3):
        proc = Process(target=run_main, args=(s, 30))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()
