# /usr/bin/python
# Last Change: Mon Oct 23 07:00 PM 2006 J

#---------------------------------------------
# This is not meant to be used yet !!!! I am 
# not sure how to integrate this stuff inside
# the package yet. The cases are:
#   - we have a set of data, and we want to test online EM 
#   compared to normal EM 
#   - we do not have all the data before putting them in online EM:
#   eg current frame depends on previous frame in some way.

# TODO:
#   - Add biblio
#   - Look back at articles for discussion for init, regularization and 
#   convergence rates
#   - the function sufficient_statistics does not really return SS. This is not a
#   big problem, but it would be better to really return them as the name implied.

import numpy as N
from numpy import mean
from numpy.testing import assert_array_almost_equal, assert_array_equal

from gmm_em import ExpMixtureModel, GMM, EM, multiple_gauss_den
from gauss_mix import GM
from kmean import kmean

import copy
from numpy.random import seed

# Clamp
clamp   = 1e-8

# Error classes
class OnGmmError(Exception):
    """Base class for exceptions in this module."""
    pass

class OnGmmParamError:
    """Exception raised for errors in gmm params

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """
    def __init__(self, message):
        self.message    = message
    
    def __str__(self):
        return self.message

class OnGMM(ExpMixtureModel):
    """A Class for 'online' (ie recursive) EM. Insteand
    of running the E step on the whole data, the sufficient statistics
    are updated for each new frame of data, and used in the (unchanged)
    M step"""
    def init_random(self, init_data):
        """ Init the model at random."""
        k   = self.gm.k
        d   = self.gm.d
        if self.gm.mode == 'diag':
            w           = N.ones(k) / k

            # Init the internal state of EM
            self.cx     = N.outer(w, mean(init_data, 0))
            self.cxx    = N.outer(w, mean(init_data ** 2, 0))

            # w, mu and va init is the same that in the standard case
            (code, label)   = kmean(init_data, init_data[0:k, :], niter)
            mu          = code.copy()
            va          = N.zeros((k, d))
            for i in range(k):
                for j in range(d):
                    va [i,j] = N.cov(init_data[N.where(label==i), j], rowvar = 0)
        else:
            raise OnGmmParamError("""init_online not implemented for
                    mode %s yet""", mode)

        self.gm.set_param(w, mu, va)
        # c* are the parameters which are computed at every step (ie
        # when a new frame is taken into account
        self.cw     = self.gm.w
        self.cmu    = self.gm.mu
        self.cva    = self.gm.va

        # p* are the parameters used when computing gaussian densities
        # they are always the same than c* in the online case
        self.pw     = self.cw
        self.pmu    = self.cmu
        self.pva    = self.cva

    def init_kmean(self, init_data, niter = 5):
        """ Init the model using kmean."""
        k   = self.gm.k
        d   = self.gm.d
        if self.gm.mode == 'diag':
            w           = N.ones(k) / k

            # Init the internal state of EM
            self.cx     = N.outer(w, mean(init_data, 0))
            self.cxx    = N.outer(w, mean(init_data ** 2, 0))

            # w, mu and va init is the same that in the standard case
            (code, label)   = kmean(init_data, init_data[0:k, :], niter)
            mu          = code.copy()
            va          = N.zeros((k, d))
            for i in range(k):
                for j in range(d):
                    va [i,j] = N.cov(init_data[N.where(label==i), j], rowvar = 0)
        else:
            raise OnGmmParamError("""init_online not implemented for
                    mode %s yet""", mode)

        self.gm.set_param(w, mu, va)
        # c* are the parameters which are computed at every step (ie
        # when a new frame is taken into account
        self.cw     = self.gm.w
        self.cmu    = self.gm.mu
        self.cva    = self.gm.va

        # p* are the parameters used when computing gaussian densities
        # they are the same than c* in the online case
        # self.pw     = self.cw.copy()
        # self.pmu    = self.cmu.copy()
        # self.pva    = self.cva.copy()
        self.pw     = self.cw
        self.pmu    = self.cmu
        self.pva    = self.cva

    def __init__(self, gm, init_data, init = 'kmean'):
        self.gm = gm
        
        # Possible init methods
        init_methods = {'kmean' : self.init_kmean}

        self.init   = init_methods[init]

    def compute_sufficient_statistics(self, frame, nu):
        """ sufficient_statistics(frame, nu)
        
        frame has to be rank 2 !"""
        gamma   = multiple_gauss_den(frame, self.pmu, self.pva)[0]
        gamma   *= self.pw
        gamma   /= N.sum(gamma)
        # <1>(t) = cw(t), each column is one component cw = (cw1, ..., cwK);
        #self.cw	= (1 - nu) * self.cw + nu * gamma
        self.cw	*= (1 - nu)
        self.cw += nu * gamma

        for k in range(self.gm.k):
            self.cx[k]   = (1 - nu) * self.cx[k] + nu * frame * gamma[k]
            self.cxx[k]  = (1 - nu) * self.cxx[k] + nu * frame ** 2 * gamma[k]

    def update_em(self):
        for k in range(self.gm.k):
            self.cmu[k]  = self.cx[k] / self.cw[k]
            self.cva[k]  = self.cxx[k] / self.cw[k] - self.cmu[k] ** 2
    
if __name__ == '__main__':
    d       = 1
    k       = 2
    mode    = 'diag'
    nframes = int(1e3)
    emiter  = 4
    seed(5)

    #+++++++++++++++++++++++++++++++++++++++++++++++++
    # Generate a model with k components, d dimensions
    #+++++++++++++++++++++++++++++++++++++++++++++++++
    w, mu, va   = GM.gen_param(d, k, mode, spread = 1.5)
    gm          = GM.fromvalues(w, mu, va)
    # Sample nframes frames  from the model
    data        = gm.sample(nframes)

    #++++++++++++++++++++++++++++++++++++++++++
    # Approximate the models with classical EM
    #++++++++++++++++++++++++++++++++++++++++++
    # Init the model
    lgm = GM(d, k, mode)
    gmm = GMM(lgm, 'kmean')
    gmm.init(data)

    gm0    = copy.copy(gmm.gm)
    # The actual EM, with likelihood computation
    like    = N.zeros(emiter)
    for i in range(emiter):
        g, tgd  = gmm.sufficient_statistics(data)
        like[i] = N.sum(N.log(N.sum(tgd, 1)), axis = 0)
        gmm.update_em(data, g)

    #++++++++++++++++++++++++++++++++++++++++
    # Approximate the models with online EM
    #++++++++++++++++++++++++++++++++++++++++
    ogm     = GM(d, k, mode)
    ogmm    = OnGMM(ogm, 'kmean')
    init_data   = data[0:nframes / 20, :]
    ogmm.init(init_data)

    # Forgetting param
    ku		= 0.005
    t0		= 200
    lamb	= 1 - 1/(N.arange(-1, nframes-1) * ku + t0)
    nu0		= 0.2
    nu		= N.zeros((len(lamb), 1))
    nu[0]	= nu0
    for i in range(1, len(lamb)):
        nu[i]	= 1./(1 + lamb[i] / nu[i-1])

    # object version of online EM
    for t in range(nframes):
        ogmm.compute_sufficient_statistics(data[t:t+1, :], nu[t])
        ogmm.update_em()

    ogmm.gm.set_param(ogmm.cw, ogmm.cmu, ogmm.cva)

    #+++++++++++++++
    # Draw the model
    #+++++++++++++++
    print "drawing..."
    import pylab as P
    P.subplot(2, 1, 1)

    if not d == 1:
        # Draw what is happening
        P.plot(data[:, 0], data[:, 1], '.', label = '_nolegend_')

        h   = gm.plot()    
        [i.set_color('g') for i in h]
        h[0].set_label('true confidence ellipsoides')

        h   = gm0.plot()    
        [i.set_color('k') for i in h]
        h[0].set_label('initial confidence ellipsoides')

        h   = lgm.plot()    
        [i.set_color('r') for i in h]
        h[0].set_label('confidence ellipsoides found by EM')

        h   = ogmm.gm.plot()    
        [i.set_color('m') for i in h]
        h[0].set_label('confidence ellipsoides found by Online EM')

        # P.legend(loc = 0)
    else:
        # Real confidence ellipses
        h   = gm.plot1d()
        [i.set_color('g') for i in h['pdf']]
        h['pdf'][0].set_label('true pdf')

        # Initial confidence ellipses as found by kmean
        h0  = gm0.plot1d()
        [i.set_color('k') for i in h0['pdf']]
        h0['pdf'][0].set_label('initial pdf')

        # Values found by EM
        hl  = lgm.plot1d(fill = 1, level = 0.66)
        [i.set_color('r') for i in hl['pdf']]
        hl['pdf'][0].set_label('pdf found by EM')

        P.legend(loc = 0)

        # Values found by Online EM
        hl  = ogmm.gm.plot1d(fill = 1, level = 0.66)
        [i.set_color('m') for i in hl['pdf']]
        hl['pdf'][0].set_label('pdf found by Online EM')

        P.legend(loc = 0)

    P.subplot(2, 1, 2)
    P.plot(nu)
    P.title('Learning rate')
    P.show()
