from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class Drum(Component):
    r"""
    Class for exergy and exergoeconomic analysis of steam drums.

    A drum separates the water/steam mixture of an evaporator circuit. It takes the feed
    water and the heating steam coming back from the evaporator, and returns saturated
    steam, the circulating water that goes back to the evaporator and, optionally, a blow
    down. At least two inlets and two outlets are required; further outlets are supported.

    All streams leaving a drum are at the same saturation state, so all of them are treated
    as products of the separation: the exergy product is the sum of all outlets and the
    exergy fuel the sum of all inlets,

    .. math::

        \dot{E}_\mathrm{P} = \sum_j \dot{E}^\mathrm{PH}_{\mathrm{out,}j} \qquad
        \dot{E}_\mathrm{F} = \sum_i \dot{E}^\mathrm{PH}_{\mathrm{in,}i}

    and in the exergoeconomic analysis every outlet carries the same specific costs (see
    :meth:`aux_eqs`). A blow down is therefore charged at the same rate as the steam and
    takes its share of the costs out of the plant; declare it in ``E_L`` to report it as a
    loss of the system.

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

    Note
    ----
    The Ebsilon steam drum (component 20) is mapped to this component: the feed water (pin 1)
    and the heating steam (pin 4) become the inlets, the circulating water (pin 3), the
    saturated steam (pin 2) and the blow down (pin 5) the outlets.
    """

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the drum.

        Parameters
        ----------
        T0 : float
            Ambient temperature T0 / K.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If fewer than two inlets or fewer than two outlets are connected.

        Note
        ----
        Please note, that the exergy balance accounts for physical exergy only. The sums run
        over all connected streams, so a third outlet such as a blow down is part of the
        exergy product instead of being ignored.

        .. math::

            \dot{E}_\mathrm{P} = \sum \dot{E}_{\mathrm{out,}j}^\mathrm{PH}\\
            \dot{E}_\mathrm{F} = \sum \dot{E}_{\mathrm{in,}i}^\mathrm{PH}
        """
        if len(self.inl) < 2 or len(self.outl) < 2:
            msg = "Drum requires at least two inlets and two outlets."
            logger.error(msg)
            raise ValueError(msg)

        # Summed over all streams, so that further outlets such as a blow down are accounted for
        self.E_P = sum(outlet["e_PH"] * outlet["m"] for outlet in self.outl.values())
        self.E_F = sum(inlet["e_PH"] * inlet["m"] for inlet in self.inl.values())

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of Drum {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""
        Auxiliary equations for the drum.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:

        (1) Chemical exergy cost equations, one per outlet (if enabled)
            - F-principle: the specific chemical cost of the inlet is passed on to every outlet
        (2) Thermal exergy cost equations, one per further outlet
            - P-principle: the specific thermal costs of all outlets are equalized
        (3) Mechanical exergy cost equations, one per further outlet
            - P-principle: the specific mechanical costs of all outlets are equalized
        (4) Thermal-mechanical coupling for outlet 0
            - P-principle: thermal and mechanical specific costs must be equal at outlet 0

        Costing convention: everything leaving a drum leaves at the same saturation state, so
        all outlets are co-products that carry the same specific costs,

        .. math::

            \frac{\dot{C}^\mathrm{T}_{\mathrm{out,}1}}{\dot{E}^\mathrm{T}_{\mathrm{out,}1}}
            = \frac{\dot{C}^\mathrm{T}_{\mathrm{out,}j}}{\dot{E}^\mathrm{T}_{\mathrm{out,}j}}
            \qquad
            \frac{\dot{C}^\mathrm{M}_{\mathrm{out,}1}}{\dot{E}^\mathrm{M}_{\mathrm{out,}1}}
            = \frac{\dot{C}^\mathrm{M}_{\mathrm{out,}j}}{\dot{E}^\mathrm{M}_{\mathrm{out,}j}}

        A blow down is costed at the same rate as the saturated steam and carries its share of
        the costs out of the plant; it is not charged back to the other outlets.

        The number of equations follows the number of outlets: the cost matrix holds two cost
        variables per outlet (three with chemical exergy) and the cost balance of the component
        covers one of them, so with :math:`N` outlets

        .. math::

            n_\mathrm{aux} = 2\,N - 1 \quad\text{and, with chemical exergy,}\quad
            n_\mathrm{aux} = 3\,N - 1

        rows are added here. A drum with a blow down therefore needs one thermal and one
        mechanical equation (and one chemical equation) more than a drum without.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature.
        equations : dict
            Dictionary for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.
        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index.
        equations : dict
            Updated dictionary with equation labels.
        """

        outlets = [self.outl[key] for key in sorted(self.outl)]
        row = counter

        # --- Chemical cost auxiliary equations: the inlet passes its specific cost to each outlet ---
        if chemical_exergy_enabled:
            for outlet in outlets:
                if self.inl[0]["e_CH"] != 0:
                    A[row, self.inl[0]["CostVar_index"]["CH"]] = 1 / self.inl[0]["E_CH"]
                else:
                    A[row, self.inl[0]["CostVar_index"]["CH"]] = 1
                if outlet["e_CH"] != 0:
                    A[row, outlet["CostVar_index"]["CH"]] = -1 / outlet["E_CH"]
                else:
                    A[row, outlet["CostVar_index"]["CH"]] = -1
                equations[row] = {
                    "kind": "aux_equality",
                    "objects": [self.name, self.inl[0]["name"], outlet["name"]],
                    "property": "c_CH",
                }
                row += 1

        # --- Thermal cost auxiliary equations: all outlets share the specific thermal cost ---
        for outlet in outlets[1:]:
            if (outlets[0]["e_T"] != 0) and (outlet["e_T"] != 0):
                A[row, outlets[0]["CostVar_index"]["T"]] = 1 / outlets[0]["E_T"]
                A[row, outlet["CostVar_index"]["T"]] = -1 / outlet["E_T"]
            elif outlets[0]["e_T"] == 0 and outlet["e_T"] != 0:
                A[row, outlets[0]["CostVar_index"]["T"]] = 1
            elif outlets[0]["e_T"] != 0 and outlet["e_T"] == 0:
                A[row, outlet["CostVar_index"]["T"]] = -1
            else:
                A[row, outlets[0]["CostVar_index"]["T"]] = 1
                A[row, outlet["CostVar_index"]["T"]] = -1
            equations[row] = {
                "kind": "aux_p_rule",
                "objects": [self.name, outlets[0]["name"], outlet["name"]],
                "property": "c_T",
            }
            row += 1

        # --- Mechanical cost auxiliary equations: all outlets share the specific mechanical cost ---
        for outlet in outlets[1:]:
            if outlets[0]["e_M"] != 0:
                A[row, outlets[0]["CostVar_index"]["M"]] = 1 / outlets[0]["E_M"]
            else:
                A[row, outlets[0]["CostVar_index"]["M"]] = 1
            if outlet["e_M"] != 0:
                A[row, outlet["CostVar_index"]["M"]] = -1 / outlet["E_M"]
            else:
                A[row, outlet["CostVar_index"]["M"]] = -1
            equations[row] = {
                "kind": "aux_p_rule",
                "objects": [self.name, outlets[0]["name"], outlet["name"]],
                "property": "c_M",
            }
            row += 1

        # --- Thermal-Mechanical coupling equation for outlet 0 ---
        # This enforces that the thermal and mechanical cost components at outlet 0 are consistent.
        if (outlets[0]["e_T"] != 0) and (outlets[0]["e_M"] != 0):
            A[row, outlets[0]["CostVar_index"]["T"]] = 1 / outlets[0]["E_T"]
            A[row, outlets[0]["CostVar_index"]["M"]] = -1 / outlets[0]["E_M"]
        elif (outlets[0]["e_T"] == 0) and (outlets[0]["e_M"] == 0):
            A[row, outlets[0]["CostVar_index"]["T"]] = 1
            A[row, outlets[0]["CostVar_index"]["M"]] = -1
        elif outlets[0]["e_T"] == 0:
            A[row, outlets[0]["CostVar_index"]["T"]] = 1
        else:
            A[row, outlets[0]["CostVar_index"]["M"]] = -1
        equations[row] = {
            "kind": "aux_equality",
            "objects": [self.name, outlets[0]["name"]],
            "property": "c_T, c_M",
        }
        row += 1

        # Set the right-hand side entries to zero for all added rows.
        for i in range(counter, row):
            b[i] = 0

        return A, b, row, equations
