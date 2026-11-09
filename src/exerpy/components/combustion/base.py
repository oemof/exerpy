from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class CombustionChamber(Component):
    r"""
    Class for exergy and exergoeconomic analysis of combustion chambers.

    This class performs exergy and exergoeconomic analysis calculations for combustion chambers,
    considering both thermal and mechanical exergy flows, as well as chemical exergy flows.
    With split physical exergy, the exergy product is the increase of the thermal exergy and the
    exergy fuel the decrease of the chemical and the mechanical exergy. Without the split, the product
    is the increase of the physical exergy and the fuel the decrease of the chemical exergy.

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

    Notes
    -----
    This component requires the calculation of both physical and chemical exergy.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the combustion chamber component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate (currency/h), default 0.0
        """
        super().__init__(**kwargs)
        # Initialize additional attributes if necessary
        self.Ex_C_col = kwargs.get("Ex_C_col", {})
        self.Z_costs = kwargs.get("Z_costs", 0.0)  # Cost rate in currency/h

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the combustion chamber.

        The sums run over all inlets and all outlets. With split physical exergy, the thermal exergy
        of fuel and oxidant is raised (product) at the expense of their chemical and mechanical
        exergy (fuel):

        .. math::
            \dot{E}_\mathrm{P} = \sum \dot{E}^{\mathrm{T}}_{\mathrm{out}}
                               - \sum \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::
            \dot{E}_\mathrm{F} = \Bigl(\sum \dot{E}^{\mathrm{CH}}_{\mathrm{in}}
                                       - \sum \dot{E}^{\mathrm{CH}}_{\mathrm{out}}\Bigr)
                               + \Bigl(\sum \dot{E}^{\mathrm{M}}_{\mathrm{in}}
                                       - \sum \dot{E}^{\mathrm{M}}_{\mathrm{out}}\Bigr)

        Without the split:

        .. math::
            \dot{E}_\mathrm{P} = \sum \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
                               - \sum \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::
            \dot{E}_\mathrm{F} = \sum \dot{E}^{\mathrm{CH}}_{\mathrm{in}}
                               - \sum \dot{E}^{\mathrm{CH}}_{\mathrm{out}}

        The exergy destruction :math:`\dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}`
        is the same in both cases.

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        p0 : float
            Ambient pressure (Pa).
        split_physical_exergy : bool
            Whether to split thermal and mechanical exergy.

        Raises
        ------
        ValueError
            If fewer than two inlets or no outlets are defined.
        """
        # Check for necessary inlet and outlet data
        if not hasattr(self, "inl") or not hasattr(self, "outl") or len(self.inl) < 2 or len(self.outl) < 1:
            msg = "CombustionChamber requires at least two inlets (air and fuel) and one outlet (exhaust)."
            logger.error(msg)
            raise ValueError(msg)

        if split_physical_exergy:
            self.E_P = self._exergy_increase("T")
            self.E_F = -self._exergy_increase("CH") - self._exergy_increase("M")
        else:
            self.E_P = self._exergy_increase("PH")
            self.E_F = -self._exergy_increase("CH")

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergetic efficiency (epsilon)
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of CombustionChamber {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def _exergy_increase(self, form):
        """Exergy flow of one form (``"T"``, ``"M"``, ``"PH"`` or ``"CH"``) of all outlets minus all inlets."""
        out = sum(stream["m"] * stream[f"e_{form}"] for stream in self.outl.values())
        return out - sum(stream["m"] * stream[f"e_{form}"] for stream in self.inl.values())

    def _cost_increase(self, form):
        """Cost rate of one exergy form of all outlets minus all inlets."""
        return sum(stream[f"C_{form}"] for stream in self.outl.values()) - sum(
            stream[f"C_{form}"] for stream in self.inl.values()
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Add auxiliary cost equations for the combustion chamber.

        The hot gas leaving the chamber is the product, so the cost of its thermal exergy is left to
        the cost balance. What the chamber does not raise is blended: the outlet takes the
        mass-weighted mean of the specific costs of the two inlets (F-principle).

        **With split physical exergy** the rule is written for the mechanical exergy; **without the
        split** the stream carries a single cost variable for its physical exergy, that variable is
        the product, and no mechanical rule exists:

        .. math::

            \dot{C}^\mathrm{PH}_\mathrm{out}
            = \dot{C}^\mathrm{PH}_{\mathrm{in},1} + \dot{C}^\mathrm{PH}_{\mathrm{in},2} + \dot{Z}

        The chemical rule is written in either mode, and a combustion chamber needs the chemical
        exergy to be enabled at all, since the fuel enters as chemical exergy.

        The two rules, as they are written into the matrix:

        1. F rule for mechanical exergy (only with split physical exergy):

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{M}}_{\text{out}}}\,\dot{C}^{\mathrm{M}}_{\text{out}}
            + \frac{\dot m_{1}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{M}}_{\text{in},1}}\,\dot{C}^{\mathrm{M}}_{\text{in},1}
            + \frac{\dot m_{2}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{M}}_{\text{in},2}}\,\dot{C}^{\mathrm{M}}_{\text{in},2}
            = 0

        2. F rule for chemical exergy:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{CH}}_{\text{out}}}\,\dot{C}^{\mathrm{CH}}_{\text{out}}{}
            + \frac{\dot m_{1}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{CH}}_{\text{in},1}}\,\dot{C}^{\mathrm{CH}}_{\text{in},1}
            + \frac{\dot m_{2}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{CH}}_{\text{in},2}}\,\dot{C}^{\mathrm{CH}}_{\text{in},2}
            = 0

        Parameters
        ----------
        A : numpy.ndarray
            Current cost matrix.
        b : numpy.ndarray
            Current RHS vector.
        counter : int
            Starting row index.
        T0 : float
            Ambient temperature.
        equations : dict or list
            Structure for equation labels.
        chemical_exergy_enabled : bool
            Must be True to include chemical exergy mixing.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        A : numpy.ndarray
            Updated cost matrix.
        b : numpy.ndarray
            Updated RHS vector.
        counter : int
            Updated row index.
        equations : dict or list
            Updated labels.

        Raises
        ------
        ValueError
            If chemical_exergy_enabled is False.
        """
        # For the combustion chamber, chemical exergy is mandatory.
        if not chemical_exergy_enabled:
            raise ValueError(
                "Chemical exergy is mandatory for the combustion chamber!",
                "Please make sure that your exergy analysis consider the chemical exergy.",
            )

        # Convert inlet and outlet dictionaries to lists for ordered access.
        inlets = list(self.inl.values())
        outlets = list(self.outl.values())

        # --- Mechanical cost auxiliary equation ---
        # Without the split the cost balance alone determines the cost of the physical exergy of the
        # outlet, so only the chemical mixing rule is needed.
        mech_row = 1 if split_physical_exergy else 0
        if split_physical_exergy:
            if outlets[0]["e_M"] != 0 and inlets[0]["e_M"] != 0 and inlets[1]["e_M"] != 0:
                A[counter, outlets[0]["CostVar_index"]["M"]] = -1 / outlets[0]["E_M"]
                A[counter, inlets[0]["CostVar_index"]["M"]] = (
                    (1 / inlets[0]["E_M"]) * inlets[0]["m"] / (inlets[0]["m"] + inlets[1]["m"])
                )
                A[counter, inlets[1]["CostVar_index"]["M"]] = (
                    (1 / inlets[1]["E_M"]) * inlets[1]["m"] / (inlets[0]["m"] + inlets[1]["m"])
                )
            else:
                # pressure can only decrease in the combustion chamber
                # (case with p_inlet = p0 and p_outlet < p0 NOT considered)
                A[counter, outlets[0]["CostVar_index"]["M"]] = 1
            equations[counter] = {
                "kind": "aux_mixing",
                "objects": [self.name, self.inl[0]["name"], self.inl[1]["name"], self.outl[0]["name"]],
                "property": "c_M",
            }

        # --- Chemical cost auxiliary equation ---
        if outlets[0]["e_CH"] != 0 and inlets[0]["e_CH"] != 0 and inlets[1]["e_CH"] != 0:
            A[counter + mech_row, outlets[0]["CostVar_index"]["CH"]] = -1 / outlets[0]["E_CH"]
            A[counter + mech_row, inlets[0]["CostVar_index"]["CH"]] = (
                (1 / inlets[0]["E_CH"]) * inlets[0]["m"] / (inlets[0]["m"] + inlets[1]["m"])
            )
            A[counter + mech_row, inlets[1]["CostVar_index"]["CH"]] = (
                (1 / inlets[1]["E_CH"]) * inlets[1]["m"] / (inlets[0]["m"] + inlets[1]["m"])
            )
        elif inlets[0]["e_CH"] == 0:
            A[counter + mech_row, inlets[0]["CostVar_index"]["CH"]] = 1
        elif inlets[1]["e_CH"] == 0:
            A[counter + mech_row, inlets[1]["CostVar_index"]["CH"]] = 1
        equations[counter + mech_row] = {
            "kind": "aux_mixing",
            "objects": [self.name, self.inl[0]["name"], self.inl[1]["name"], self.outl[0]["name"]],
            "property": "c_CH",
        }

        # Set the right-hand side entries to zero.
        b[counter] = 0
        b[counter + mech_row] = 0

        return [A, b, counter + mech_row + 1, equations]

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the combustion chamber.

        .. math::
            \dot{C}^{\mathrm{PH}}_{\text{in},1} + \dot{C}^{\mathrm{CH}}_{\text{in},1}
            + \dot{C}^{\mathrm{CH}}_{\text{in},2} + \dot{C}^{\mathrm{PH}}_{\text{in},2}
            - \dot{C}^{\mathrm{PH}}_{\text{out}} - \dot{C}^{\mathrm{CH}}_{\text{out}}
            + \dot{Z} = 0

        This method computes cost coefficients and ratios. Fuel and product take the same exergy
        forms as in :meth:`calc_exergy_balance`, summed over all inlets and outlets. With split
        physical exergy:

        .. math::
            \dot{C}_\mathrm{P} = \sum \dot{C}^{\mathrm{T}}_{\mathrm{out}}
                               - \sum \dot{C}^{\mathrm{T}}_{\mathrm{in}}

        .. math::
            \dot{C}_\mathrm{F} = \Bigl(\sum \dot{C}^{\mathrm{CH}}_{\mathrm{in}}
                                       - \sum \dot{C}^{\mathrm{CH}}_{\mathrm{out}}\Bigr)
                               + \Bigl(\sum \dot{C}^{\mathrm{M}}_{\mathrm{in}}
                                       - \sum \dot{C}^{\mathrm{M}}_{\mathrm{out}}\Bigr)

        Without the split:

        .. math::
            \dot{C}_\mathrm{P} = \sum \dot{C}^{\mathrm{PH}}_{\mathrm{out}}
                               - \sum \dot{C}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::
            \dot{C}_\mathrm{F} = \sum \dot{C}^{\mathrm{CH}}_{\mathrm{in}}
                               - \sum \dot{C}^{\mathrm{CH}}_{\mathrm{out}}

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        if split_physical_exergy:
            self.C_P = self._cost_increase("T")
            self.C_F = -self._cost_increase("CH") - self._cost_increase("M")
        else:
            self.C_P = self._cost_increase("PH")
            self.C_F = -self._cost_increase("CH")
        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
