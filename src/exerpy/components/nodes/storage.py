import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class Storage(Component):
    r"""
    Class for exergy and exergoeconomic analysis of a storage.

    This class performs exergy and exergoeconomic analysis calculations for storage components,
    accounting for one inlet and one outlet stream.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\mathrm{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\mathrm{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\mathrm{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    inl : dict
        Dictionary containing inlet stream data with mass flows and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with mass flows and specific exergies.
    Z_costs : float
        Investment cost rate of the component in currency/h.
    C_P : float
        Cost of product stream :math:`\dot{C}_P` in currency/h.
    C_F : float
        Cost of fuel stream :math:`\dot{C}_F` in currency/h.
    C_D : float
        Cost of exergy destruction :math:`\dot{C}_D` in currency/h.
    c_P : float
        Specific cost of product stream (currency per unit exergy).
    c_F : float
        Specific cost of fuel stream (currency per unit exergy).
    r : float
        Relative cost difference, :math:`(c_P - c_F)/c_F`.
    f : float
        Exergoeconomic factor, :math:`\dot{Z}/(\dot{Z} + \dot{C}_D)`.
    Ex_C_col : dict
        Custom cost coefficients collection passed via `kwargs`.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the storage component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """
        self.dissipative = False
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the storage.

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.
        p0 : float
            Ambient pressure in Pascal.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Notes
        -----
        The exergy analysis considers the cases where the storage is either charged or discharged.

        Case 1 (Charging):

        .. math::

            \dot{E}_\mathrm{F} = \dot{E}_\mathrm{in}^\mathrm{PH} - \dot{E}_\mathrm{out}^\mathrm{PH}

        .. math::
            \dot{E}_\mathrm{P} = (\dot{m}_\mathrm{in} - \dot{m}_\mathrm{out}) \cdot e_\mathrm{out}^\mathrm{PH}


        Case 2 (Discharging):

        .. math::

            \dot{E}_\mathrm{F} = (\dot{m}_\mathrm{out} - \dot{m}_\mathrm{in}) \cdot e_\mathrm{out}^\mathrm{PH}

        .. math::

            \dot{E}_\mathrm{P} = \dot{E}_\mathrm{out}^\mathrm{PH} - \dot{E}_\mathrm{in}^\mathrm{PH}

        """

        inlet, outlet = self._streams()
        E_in = inlet["m"] * inlet["e_PH"]
        E_out = outlet["m"] * outlet["e_PH"]

        if inlet["m"] > outlet["m"]:
            logger.info(f"Storage '{self.name}' is charged.")
            self.charging = True
            # The exergy is stored at the state of the outlet.
            self.E_stored = (inlet["m"] - outlet["m"]) * outlet["e_PH"]
            self.E_F = E_in - E_out
            self.E_P = self.E_stored
        elif inlet["m"] < outlet["m"]:
            logger.info(f"Storage '{self.name}' is discharged.")
            self.charging = False
            self.E_stored = (outlet["m"] - inlet["m"]) * outlet["e_PH"]
            self.E_F = self.E_stored
            self.E_P = E_out - E_in
        else:
            logger.info(f"Storage '{self.name}' holds its level; it passes its stream through.")
            self.charging = True
            self.E_stored = 0.0
            self.E_F = E_in
            self.E_P = E_out

        self.E_D = self.E_F - self.E_P
        self.epsilon = self.E_P / self.E_F if self.E_F != 0 else np.nan

        # Log the results.
        logger.info(
            f"Exergy balance of Storage {self.name} calculated: "
            f"E_F = {self.E_F:.2f} W, E_P = {self.E_P:.2f} W, E_D = {self.E_D:.2f} W, "
        )

    def _streams(self):
        """Return the inlet and the outlet of the storage."""
        if len(self.inl) != 1 or len(self.outl) != 1:
            msg = f"Storage {self.name} needs exactly one inlet and one outlet."
            logger.error(msg)
            raise ValueError(msg)
        return next(iter(self.inl.values())), next(iter(self.outl.values()))

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Cost balance and auxiliary equations for the storage.

        A storage that charges or discharges does not balance over its streams alone: part of the
        exergy stays behind in the store or comes out of it. That share carries a cost variable of
        its own, :math:`\dot{C}_\mathrm{stored}`, which the analysis allocates for the component,
        so the cost balance is written here and not by the generic one:

        .. math::

            \sum \dot{C}_\mathrm{in} + \dot{Z} = \sum \dot{C}_\mathrm{out}
            \pm \dot{C}_\mathrm{stored}

        with the stored cost on the side it flows to.

        The store is filled at the state of the outlet, so what goes into it or comes out of it is
        priced like the outlet. With split physical exergy that is its thermal exergy, without the
        split its physical exergy:

        .. math::

            \frac{\dot{C}_\mathrm{stored}}{\dot{E}_\mathrm{stored}}
            = \frac{\dot{C}^\mathrm{T}_\mathrm{out}}{\dot{E}^\mathrm{T}_\mathrm{out}}
            \qquad \text{or} \qquad
            \frac{\dot{C}_\mathrm{stored}}{\dot{E}_\mathrm{stored}}
            = \frac{\dot{C}^\mathrm{PH}_\mathrm{out}}{\dot{E}^\mathrm{PH}_\mathrm{out}}

        A storage holding its level stores nothing, and the variable is fixed at zero instead, since
        the specific cost of nothing is undefined:

        .. math::

            \dot{C}_\mathrm{stored} = 0
            \qquad \text{for} \qquad \dot{E}_\mathrm{stored} = 0

        What the storage does not raise passes through at its own specific cost (F-principle). That
        is the mechanical exergy with the split, and the chemical exergy when it is enabled; without
        the split there is no mechanical cost variable and this rule is not written:

        .. math::

            \frac{\dot{C}^\mathrm{M}_\mathrm{in}}{\dot{E}^\mathrm{M}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{M}_\mathrm{out}}{\dot{E}^\mathrm{M}_\mathrm{out}}
            \qquad
            \frac{\dot{C}^\mathrm{CH}_\mathrm{in}}{\dot{E}^\mathrm{CH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{CH}_\mathrm{out}}{\dot{E}^\mathrm{CH}_\mathrm{out}}

        Parameters
        ----------
        A : numpy.ndarray
            Coefficient matrix of the cost equation system.
        b : numpy.ndarray
            Right-hand side vector of the cost equation system.
        counter : int
            Index of the next free row.
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        equations : dict
            Dictionary documenting the equations.
        chemical_exergy_enabled : bool
            Whether chemical exergy is part of the analysis.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        tuple
            The updated matrix, vector, row index and equation dictionary.

        Raises
        ------
        ValueError
            If the analysis did not allocate a cost variable for the stored exergy.
        """
        inlet, outlet = self._streams()
        stored = getattr(self, "stored_cost_index", None)
        if stored is None:
            msg = f"Storage {self.name} has no cost variable for its stored exergy."
            logger.error(msg)
            raise ValueError(msg)

        labels = ["T", "M"] if split_physical_exergy else ["PH"]
        if chemical_exergy_enabled:
            labels.append("CH")
        product = "T" if split_physical_exergy else "PH"

        # Cost balance. The stored exergy leaves the component while it charges and enters it
        # while it discharges.
        for label in labels:
            A[counter, inlet["CostVar_index"][label]] = 1
            A[counter, outlet["CostVar_index"][label]] = -1
        A[counter, stored] = -1 if self.charging else 1
        equations[counter] = {"kind": "cost_balance", "objects": [self.name], "property": "Z_costs"}
        b[counter] = -self.Z_costs
        counter += 1

        # The stored exergy is priced like the physical exergy of the outlet.
        E_product = outlet[f"E_{product}"]
        if self.E_stored and E_product:
            A[counter, stored] = 1 / self.E_stored
            A[counter, outlet["CostVar_index"][product]] = -1 / E_product
        else:
            A[counter, stored] = 1
        equations[counter] = {
            "kind": "aux_p_rule",
            "objects": [self.name, outlet["name"]],
            "property": f"c_{product}",
        }
        b[counter] = 0
        counter += 1

        for label in labels:
            if label == product:
                continue
            A[counter, inlet["CostVar_index"][label]] = 1 / inlet[f"E_{label}"] if inlet[f"e_{label}"] != 0 else 1
            A[counter, outlet["CostVar_index"][label]] = -1 / outlet[f"E_{label}"] if outlet[f"e_{label}"] != 0 else -1
            equations[counter] = {
                "kind": "aux_f_rule",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": f"c_{label}",
            }
            b[counter] = 0
            counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform the exergoeconomic cost balance of the storage.

        Fuel and product follow :meth:`calc_exergy_balance`: while the storage charges, the fuel is
        what the stream gives up and the product is what goes into the store; while it discharges,
        the store is the fuel and the gain of the stream is the product. A storage holding its
        level is costed like a pipe.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        inlet, outlet = self._streams()
        labels = ["C_T", "C_M"] if split_physical_exergy else ["C_PH"]
        if chemical_exergy_enabled:
            labels.append("C_CH")

        C_in = sum(inlet[label] for label in labels)
        C_out = sum(outlet[label] for label in labels)
        C_stored = getattr(self, "C_stored", 0.0)
        self.C_stored_flow = -C_stored if self.charging else C_stored

        if not self.E_stored:
            self.C_F = C_in
            self.C_P = C_out
        elif self.charging:
            self.C_F = C_in - C_out
            self.C_P = C_stored
        else:
            self.C_F = C_stored
            self.C_P = C_out - C_in

        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
