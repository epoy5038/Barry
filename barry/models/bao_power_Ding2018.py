import logging
from functools import lru_cache
import numpy as np
from scipy import integrate
from scipy.special import jn
from barry.models.bao_power import PowerSpectrumFit
from scipy.interpolate import splev, splrep


class PowerDing2018(PowerSpectrumFit):
    """P(k) model inspired from Ding 2018.

    See https://ui.adsabs.harvard.edu/abs/2018MNRAS.479.1021D for details.

    """

    def __init__(
        self,
        name="Pk Ding 2018",
        fix_params=("om", "beta"),
        smooth_type=None,
        recon=None,
        postprocess=None,
        smooth=False,
        correction=None,
        isotropic=True,
        poly_poles=(0, 2),
        marg=None,
        n_poly=5,
        n_data=1,
        data_share_bias=False,
        data_share_poly=False,
    ):

        if n_poly not in [0, 3, 5]:
            raise NotImplementedError("Models require n_poly to be 0, 3 or 5 polynomial terms per multipole")

        self.marg_bias = False

        super().__init__(
            name=name,
            fix_params=fix_params,
            smooth_type=smooth_type,
            postprocess=postprocess,
            recon=recon,
            smooth=smooth,
            correction=correction,
            isotropic=isotropic,
            poly_poles=poly_poles,
            marg=marg,
            n_poly=n_poly,
            n_data=n_data,
            data_share_bias=data_share_bias,
            data_share_poly=data_share_poly,
        )

        if self.recon_type == "sym" or self.recon_type == "ani":
            raise NotImplementedError("Symmetric and Anisotropic reconstruction not yet available for Ding2018 model")

        self.set_marg(fix_params, poly_poles, n_poly)

    def precompute(self, camb, om, h0):

        c = camb.get_data(om, h0)
        r_drag = c["r_s"]
        ks = c["ks"]
        pk_lin = c["pk_lin"]
        j0 = jn(0, r_drag * ks)
        s = camb.smoothing_kernel

        return {
            "sigma_nl": integrate.simps(pk_lin * (1.0 - j0), ks) / (6.0 * np.pi**2),
            "sigma_dd_nl": integrate.simps(pk_lin * (1.0 - s) ** 2 * (1.0 - j0), ks) / (6.0 * np.pi**2),
            "sigma_sd_nl": integrate.simps(pk_lin * (0.5 * (s**2 + (1.0 - s) ** 2) + j0 * s * (1.0 - s)), ks)
            / (6.0 * np.pi**2),  # Corrected for sign error in front of j0.
            "sigma_ss_nl": integrate.simps(pk_lin * s**2 * (1.0 - j0), ks) / (6.0 * np.pi**2),
        }

    @lru_cache(maxsize=4)
    def get_damping(self, growth, om):
        return np.exp(-np.outer(1.0 + (2.0 + growth) * growth * self.mu**2, self.camb.ks**2) * self.get_pregen("sigma_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_dd(self, growth, om):
        return np.exp(-np.outer(1.0 + (2.0 + growth) * growth * self.mu**2, self.camb.ks**2) * self.get_pregen("sigma_dd_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_sd(self, growth, om):
        return np.exp(-np.outer(1.0 + growth * self.mu**2, self.camb.ks**2) * self.get_pregen("sigma_sd_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_ss(self, om):
        return np.exp(-np.tile(self.camb.ks**2, (self.nmu, 1)) * self.get_pregen("sigma_ss_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_par(self, growth, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer((1.0 + (2.0 + growth) * growth) * ks**2, self.mu**2) * self.get_pregen("sigma_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_perp(self, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer(ks**2, 1.0 - self.mu**2) * self.get_pregen("sigma_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_dd_par(self, growth, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer((1.0 + (2.0 + growth) * growth) * ks**2, self.mu**2) * self.get_pregen("sigma_dd_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_dd_perp(self, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer(ks**2, 1.0 - self.mu**2) * self.get_pregen("sigma_dd_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_sd_par(self, growth, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer((1.0 + growth) * ks**2, self.mu**2) * self.get_pregen("sigma_sd_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_sd_perp(self, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer(ks**2, 1.0 - self.mu**2) * self.get_pregen("sigma_sd_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_ss_par(self, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer(ks**2, self.mu**2) * self.get_pregen("sigma_ss_nl", om))

    @lru_cache(maxsize=4)
    def get_damping_aniso_ss_perp(self, om, data_name=None):
        if data_name is None:
            ks = self.camb.ks
        else:
            ks = self.data_dict[data_name]["ks_input"]
        return np.exp(-np.outer(ks**2, 1.0 - self.mu**2) * self.get_pregen("sigma_ss_nl", om))

    def declare_parameters(self):
        super().declare_parameters()
        self.add_param("beta", r"$\beta$", 0.01, 4.0, 0.5)  # RSD parameter f/b
        self.add_param("sigma_s", r"$\Sigma_s$", 0.01, 10.0, 5.0)  # Fingers-of-god damping
        self.add_param("b_delta", r"$b_{\delta}$", -5.0, 5.0, 0.0)  # Non-linear galaxy bias
        for i in range(self.n_data_poly):
            for pole in self.poly_poles:
                if self.n_poly >= 3:
                    self.add_param(f"a{{{pole}}}_1_{{{i+1}}}", f"$a_{{{pole},1,{i+1}}}$", -20000.0, 20000.0, 0)
                    self.add_param(f"a{{{pole}}}_2_{{{i+1}}}", f"$a_{{{pole},2,{i+1}}}$", -20000.0, 20000.0, 0)
                    self.add_param(f"a{{{pole}}}_3_{{{i+1}}}", f"$a_{{{pole},3,{i+1}}}$", -5000.0, 5000.0, 0)
                if self.n_poly == 5:
                    self.add_param(f"a{{{pole}}}_4_{{{i+1}}}", f"$a_{{{pole},4,{i+1}}}$", -200.0, 200.0, 0)
                    self.add_param(f"a{{{pole}}}_5_{{{i+1}}}", f"$a_{{{pole},5,{i+1}}}$", -3.0, 3.0, 0)

    def compute_power_spectrum(self, k, p, smooth=False, for_corr=False, data_name=None):
        """Computes the power spectrum model using the Ding et. al., 2018 EFT0 propagator

        Parameters
        ----------
        k : np.ndarray
            Array of (undilated) k-values to compute the model at.
        p : dict
            dictionary of parameter names to their values
        smooth : bool, optional
            Whether or not to generate a smooth model without the BAO feature
        shape : bool, optional
            Whether or not to include shape marginalisation terms.
        dilate : bool, optional
            Whether or not to dilate the k-values of the model based on the values of alpha (and epsilon)

        Returns
        -------
        kprime : np.ndarray
            Wavenumbers of the computed pk
        pk0 : np.ndarray
            the model monopole interpolated to kprime.
        pk2 : np.ndarray
            the model quadrupole interpolated to kprime. Will be 'None' if the model is isotropic
        pk4 : np.ndarray
            the model hexadecapole interpolated to kprime. Will be 'None' if the model is isotropic

        """

        # Get the basic power spectrum components
        if self.kvals is None or self.pksmooth is None or self.pkratio is None:
            ks = self.camb.ks
            pk_smooth_lin, pk_ratio = self.compute_basic_power_spectrum(p["om"])
        else:
            ks = self.kvals
            pk_smooth_lin, pk_ratio = self.pksmooth, self.pkratio

        if not for_corr:
            if "b" not in p:
                p = self.deal_with_ndata(p, 0)

        if self.isotropic:

            pk = [np.zeros(len(k))]

            kprime = k if for_corr else k / p["alpha"]

            # Compute the smooth model
            fog = 1.0 / (1.0 + np.outer(self.mu**2, ks**2 * p["sigma_s"] ** 2 / 2.0)) ** 2
            pk_smooth = p["b"] ** 2 * pk_smooth_lin * fog

            if smooth:
                propagator = np.zeros(len(ks))
            else:
                # Lets round some things for the sake of numerical speed
                om = np.round(p["om"], decimals=5)
                growth = np.round(p["b"] * p["beta"], decimals=5)

                # Compute the BAO damping
                if self.recon:
                    damping_dd = self.get_damping_dd(growth, om)
                    damping_sd = self.get_damping_sd(growth, om)
                    damping_ss = self.get_damping_ss(om)

                    smooth_prefac = np.tile(self.camb.smoothing_kernel / p["b"], (self.nmu, 1))
                    bdelta_prefac = np.tile(0.5 * p["b_delta"] / p["b"] * ks**2, (self.nmu, 1))
                    kaiser_prefac = (
                        1.0 - smooth_prefac + np.outer(p["beta"] * self.mu**2, 1.0 - self.camb.smoothing_kernel) + bdelta_prefac
                    )
                    propagator = (
                        (kaiser_prefac**2 - bdelta_prefac**2) * damping_dd
                        + 2.0 * kaiser_prefac * smooth_prefac * damping_sd
                        + smooth_prefac**2 * damping_ss
                    )
                else:
                    damping = self.get_damping(growth, om)
                    bdelta_prefac = np.tile(0.5 * p["b_delta"] / p["b"] * ks**2, (self.nmu, 1))
                    kaiser_prefac = 1.0 + np.tile(p["beta"] * self.mu**2, (len(ks), 1)).T + bdelta_prefac
                    propagator = (kaiser_prefac**2 - bdelta_prefac**2) * damping

            if smooth:
                prefac = np.ones(len(kprime))
            else:
                prefac = splev(kprime, splrep(ks, integrate.simps((1.0 + pk_ratio * propagator), self.mu, axis=0)))

            if for_corr:
                poly = None
                pk1d = integrate.simps(pk_smooth * (1.0 + pk_ratio * propagator), self.mu, axis=0)
            else:
                shape, poly = (
                    self.add_three_poly(ks, k, p, prefac, np.zeros(len(k)))
                    if self.n_poly == 3
                    else self.add_five_poly(ks, k, p, prefac, np.zeros(len(k)))
                )
                if self.marg:
                    poly = poly[1:]  # Remove the bias marginalisation.
                pk1d = integrate.simps((pk_smooth + shape) * (1.0 + pk_ratio * propagator), self.mu, axis=0)

            pk[0] = splev(kprime, splrep(ks, pk1d))

        else:
            epsilon = np.round(p["epsilon"], decimals=5)
            kprime = np.tile(k, (self.nmu, 1)).T if for_corr else np.outer(k / p["alpha"], self.get_kprimefac(epsilon))
            muprime = self.get_muprime(epsilon)
            fog = 1.0 / (1.0 + muprime**2 * kprime**2 * p["sigma_s"] ** 2 / 2.0) ** 2

            # Lets round some things for the sake of numerical speed
            om = np.round(p["om"], decimals=5)
            growth = np.round(p["b"] * p["beta"], decimals=5)

            sprime = splev(kprime, splrep(ks, self.camb.smoothing_kernel)) if self.recon else 0.0
            kaiser_prefac = 1.0 + p["beta"] * muprime**2 * (1.0 - sprime)

            pk_smooth = p["b"] ** 2 * kaiser_prefac**2 * splev(kprime, splrep(ks, pk_smooth_lin)) * fog

            if smooth:
                pk2d = pk_smooth
            else:
                # Compute the BAO damping
                power_par = 1.0 / (p["alpha"] ** 2 * (1.0 + epsilon) ** 4)
                power_perp = (1.0 + epsilon) ** 2 / p["alpha"] ** 2
                bdelta_prefac = 0.5 * p["b_delta"] / (p["b"] * kaiser_prefac) * kprime**2
                if self.recon:
                    damping_dd = (
                        self.get_damping_aniso_dd_par(growth, om, data_name=data_name) ** power_par
                        * self.get_damping_aniso_dd_perp(om, data_name=data_name) ** power_perp
                    )
                    damping_sd = (
                        self.get_damping_aniso_sd_par(growth, om, data_name=data_name) ** power_par
                        * self.get_damping_aniso_sd_perp(om, data_name=data_name) ** power_perp
                    )
                    damping_ss = (
                        self.get_damping_aniso_ss_par(om, data_name=data_name) ** power_par
                        * self.get_damping_aniso_ss_perp(om, data_name=data_name) ** power_perp
                    )

                    # Compute propagator
                    smooth_prefac = sprime / (p["b"] * kaiser_prefac)
                    propagator = (
                        ((1.0 + bdelta_prefac - smooth_prefac) ** 2 - bdelta_prefac**2) * damping_dd
                        + 2.0 * (1.0 + bdelta_prefac - smooth_prefac) * smooth_prefac * damping_sd
                        + smooth_prefac**2 * damping_ss
                    )
                else:
                    damping = (
                        self.get_damping_aniso_par(growth, om, data_name=data_name) ** power_par
                        * self.get_damping_aniso_perp(om, data_name=data_name) ** power_perp
                    )

                    # Compute propagator
                    propagator = (1.0 + 2.0 * bdelta_prefac) * damping

                pk2d = pk_smooth * (1.0 + splev(kprime, splrep(ks, pk_ratio)) * propagator)

            pk0, pk2, pk4 = self.integrate_mu(pk2d)

            # Polynomial shape
            pk = [pk0, np.zeros(len(k)), pk2, np.zeros(len(k)), pk4, np.zeros(len(k))]

            if for_corr:
                poly = None
                kprime = k
            else:
                shape, poly = (
                    self.add_three_poly(k, k, p, np.ones(len(k)), pk)
                    if self.n_poly == 3
                    else self.add_five_poly(k, k, p, np.ones(len(k)), pk)
                )
                if self.marg:
                    poly = poly[1:]  # Remove the bias marginalisation.
                else:
                    for pole in self.poly_poles:
                        pk[pole] += shape[pole]

        return kprime, pk, poly


if __name__ == "__main__":
    import sys

    sys.path.append("../..")
    from barry.datasets.dataset_power_spectrum import PowerSpectrum_SDSS_DR12
    from barry.config import setup_logging
    from barry.models.model import Correction

    setup_logging()

    print("Checking isotropic mock mean")
    dataset = PowerSpectrum_SDSS_DR12(isotropic=True, recon="iso")
    model = PowerDing2018(recon=dataset.recon, marg="full", isotropic=dataset.isotropic, correction=Correction.HARTLAP)
    model.sanity_check(dataset)

    print("Checking anisotropic mock mean")
    dataset = PowerSpectrum_SDSS_DR12(realisation=0, isotropic=False, fit_poles=[0, 2], recon="iso", galactic_cap="both")
    model = PowerDing2018(
        recon=dataset.recon,
        isotropic=dataset.isotropic,
        marg="full",
        fix_params=["om"],
        poly_poles=[0, 2],
        correction=Correction.HARTLAP,
        n_data=2,
        data_share_bias=False,
        data_share_poly=True,
        n_poly=5,
    )
    model.sanity_check(dataset)
