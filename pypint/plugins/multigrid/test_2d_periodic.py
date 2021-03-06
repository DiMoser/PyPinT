# coding=utf-8
import numpy as np
import sys
print(sys.path)
from pypint.plugins.multigrid.multigrid_problem import MultiGridProblem
from pypint.plugins.multigrid.multigrid_level_provider import MultiGridLevelProvider
from pypint.plugins.multigrid.multigrid_solution import MultiGridSolution
from pypint.plugins.multigrid.level2d import MultigridLevel2D
from pypint.plugins.multigrid.multigrid_smoother import ILUSmoother, SplitSmoother, DirectSolverSmoother, WeightedJacobiSmoother
from pypint.utilities import assert_is_callable, assert_is_instance, assert_condition
from pypint.plugins.multigrid.stencil import Stencil
from pypint.plugins.multigrid.interpolation import InterpolationByStencilListIn1D, InterpolationByStencilForLevels, InterpolationByStencilForLevelsClassical
from pypint.plugins.multigrid.restriction import RestrictionStencilPure, RestrictionByStencilForLevels, RestrictionByStencilForLevelsClassical
from operator import iadd,add
import matplotlib.pyplot as plt

if __name__ == '__main__':

    np.set_printoptions(precision=4, edgeitems=4, threshold=10)
    laplace_array = np.asarray([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]])
    laplace_stencil = Stencil(np.asarray([[0, 1, 0], [1, -4, 1], [0, 1, 0]]), None, 2)
    geo = np.asarray([[0, np.pi * 2], [0, np.pi * 2]])
    rhs_function = lambda x, y: 0.0

    east_f = lambda x: np.sin(x[1]*np.pi)
    west_f = lambda x: np.sin(x[1]*np.pi)
    north_f = lambda x: np.sin(x[0]*np.pi)
    south_f = lambda x: np.sin(x[0]*np.pi)

    boundary_functions = [[west_f, east_f], [north_f, south_f]]

    mg_problem = MultiGridProblem(laplace_stencil,
                                  rhs_function,
                                  boundary_functions=boundary_functions,
                                  boundaries="periodic",
                                  geometry=geo)

    level = MultigridLevel2D((10, 10),
                             mg_problem=mg_problem,
                             max_borders=np.asarray([[1, 1], [1, 1]]),
                             role="FL")

    level.mid[:] = np.sin(level.mid_tensor[0])*np.cos(level.mid_tensor[1])
    print("Level.arr before padding\n", level.arr)
    level.pad()
    print("Level.arr after padding\n", level.arr)
    # periodic padding works, that means the v cycle should work fine

    n_jacobi_pre = 5
    n_jacobi_post = 5
    borders = np.ones((2, 2))
    top_level = MultigridLevel2D((259, 259), mg_problem=mg_problem,
                                 max_borders=borders, role="FL")



    mid_level = MultigridLevel2D((129, 129), mg_problem=mg_problem,
                                 max_borders=borders, role="ML")

    low_level = MultigridLevel2D((64, 64), mg_problem=mg_problem,
                                 max_borders=borders, role="CL")
    mg_problem.fill_rhs(top_level)
    top_level.pad()


    # define the different stencils
    top_stencil = Stencil(laplace_array/top_level.h[0]**2, None, 2)
    mid_stencil = Stencil(laplace_array/mid_level.h[0]**2, None, 2)
    low_stencil = Stencil(laplace_array/low_level.h[0]**2, None, 2)
    top_stencil.modify_rhs(top_level)

    omega = 2.0/3.0
    l_plus = np.asarray([[0, 0, 0],
                         [0, -4.0/omega, 0],
                         [0, 0, 0]])
    l_minus = np.asarray([[0, 1.0, 0], [1.0, -4.0*(1.0 - 1.0/omega), 1.0], [0., 1., 0.]])

    # define the different smoothers on each level, works just for symmetric grids
    top_jacobi_smoother = SplitSmoother(l_plus / top_level.h[0]**2,
                                        l_minus / top_level.h[0]**2,
                                        top_level)
    mid_jacobi_smoother = SplitSmoother(l_plus / mid_level.h[0]**2,
                                        l_minus / mid_level.h[0]**2,
                                        mid_level)
    low_jacobi_smoother = SplitSmoother(l_plus / low_level.h[0]**2,
                                        l_minus / low_level.h[0]**2,
                                        low_level)
    low_direct_smoother = DirectSolverSmoother(low_stencil, low_level)

    # prepare the ilu smoother
    top_ilu_smoother = ILUSmoother(top_stencil, top_level)
    mid_ilu_smoother = ILUSmoother(mid_stencil, mid_level)
    low_ilu_smoother = ILUSmoother(low_stencil, low_level)

    # define the the restriction operators - full weighting
    rst_stencil = Stencil(np.asarray([[1.0, 2.0, 1.0], [2.0, 4.0, 2.0], [1.0, 2.0, 1.0]])/16)
    rst_top_to_mid = RestrictionByStencilForLevelsClassical(top_level, mid_level, rst_stencil)
    rst_mid_to_low = RestrictionByStencilForLevelsClassical(mid_level, low_level, rst_stencil)

    # define the interpolation
    corner_array = np.ones((2., 2.)) * 0.25
    border_arr_h = np.asarray([[0.5, 0.5]])
    border_arr_v = np.asarray([[0.5], [0.5]])

    ipl_stencil_list = [(Stencil(np.asarray([[1]])), (1, 1)),
                        (Stencil(corner_array), (0, 0)),
                        (Stencil(border_arr_h), (1, 0)),
                        (Stencil(border_arr_v), (0, 1))]

    ipl_mid_to_top = InterpolationByStencilForLevelsClassical(mid_level, top_level, ipl_stencil_list, pre_assign=iadd)
    ipl_low_to_mid = InterpolationByStencilForLevelsClassical(low_level, mid_level, ipl_stencil_list, pre_assign=iadd)

    print("==== Down The V Cycle ====")
    print("** Initial TopLevel.arr **\n", top_level.arr)
    # top_jacobi_smoother.relax(n_jacobi_pre)
    # print("** TopLevel.arr after "+str(n_jacobi_pre)+" jacobi step(s) **\n", top_level.arr)

    top_ilu_smoother.relax(n_jacobi_pre)
    print("** TopLevel.arr after "+str(n_jacobi_pre)+" ilu step(s) **\n", top_level.arr)

    print("** TopLevel.res before computation **\n", top_level.res)
    top_level.compute_residual(top_stencil)
    print("** TopLevel.res after computation **\n", top_level.res)
    print("** MidLevel.rhs before restriction **\n", mid_level.rhs)
    rst_top_to_mid.restrict()
    print("** MidLevel.rhs after restriction **\n", mid_level.rhs)

    # mid_jacobi_smoother.relax(n_jacobi_pre)
    # print("** MidLevel.arr after "+str(n_jacobi_pre)+" jacobi step(s) **\n", mid_level.arr)

    mid_ilu_smoother.relax(n_jacobi_pre)
    print("** MidLevel.arr after "+str(n_jacobi_pre)+" ilu step(s) **\n", mid_level.arr)

    print("** MidLevel.res before computation **\n", mid_level.res)
    mid_level.compute_residual(mid_stencil)
    print("** MidLevel.res after computation **\n", mid_level.res)

    print("** LowLevel.rhs before restriction **\n", low_level.rhs)
    rst_mid_to_low.restrict()
    print("** LowLevel.rhs after restriction **\n", low_level.rhs)
    # low_jacobi_smoother.relax(n_jacobi_pre)
    # print("** LowLevel.arr after "+str(n_jacobi_pre)+" jacobi step(s) **\n", low_level.arr)
    low_direct_smoother.relax()
    # low_level.mid[:] = (np.arange(4).reshape((2, 2)) + 1)**2
    print("** LowLevel.arr after direct solve **\n", low_level.arr)
    print("** MidLevel.arr before interpolation **\n", mid_level.arr)
    # mid_level.mid[:] = 0.0
    ipl_low_to_mid.eval()
    print("** MidLevel.arr after interpolation **\n", mid_level.arr)
    # mid_jacobi_smoother.relax(n_jacobi_post)
    # print("** MidLevel.arr after "+str(n_jacobi_post)+" jacobi step(s) **\n", mid_level.arr)

    mid_ilu_smoother.relax(n_jacobi_post)
    print("** MidLevel.arr after "+str(n_jacobi_post)+" ilu step(s) **\n", mid_level.arr)

    ipl_mid_to_top.eval()
    print("** TopLevel.arr after interpolation **\n", top_level.arr)

    # top_jacobi_smoother.relax(n_jacobi_post)
    # print("** TopLevel.arr after "+str(n_jacobi_post)+" jacobi step(s) **\n", top_level.arr)

    top_ilu_smoother.relax(n_jacobi_post)
    print("** TopLevel.arr after "+str(n_jacobi_post)+" ilu step(s) **\n", top_level.arr)

    sol_level = MultigridLevel2D((259, 259),
                             mg_problem=mg_problem,
                             max_borders=np.asarray([[1, 1], [1, 1]]),
                             role="FL")
    sol_level.rhs[:] = 0.0
    sol_level.pad()
    sol_stencil = Stencil(laplace_array/sol_level.h[0]**2, None, 2)
    sol_stencil.modify_rhs(sol_level)
    # print("I am modified", sol_level.modified_rhs)
    direct_solver = DirectSolverSmoother(sol_stencil, sol_level)
    direct_solver.relax()
    print("** The collocation solution **\n", sol_level.arr)
    print("** The error **\n", sol_level.mid - top_level.mid)

    # plot the data
    # shade data, creating an rgb array.
    # plot un-shaded and shaded images.

    plt.imshow(top_level.arr, cmap=plt.cm.coolwarm)
    plt.title('periodische Randbedingungen')
    plt.xticks([]); plt.yticks([])
    plt.colorbar(cmap=plt.cm.coolwarm)
    plt.show()
