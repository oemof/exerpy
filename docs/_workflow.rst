.. list-table:: From the model to the cost of the product
    :header-rows: 1
    :widths: 4 22 26 24 24

    * -
      - Step
      - Needs
      - Gives
      - Examples
    * - 1
      - :ref:`Exergy analysis <exergy_analysis_label>`
      - a model from Ebsilon, Aspen Plus, TESPy or JSON; fuel, product and loss of the plant
      - :math:`\dot{E}_\mathrm{F}`, :math:`\dot{E}_\mathrm{P}`, :math:`\dot{E}_\mathrm{D}` and
        :math:`\varepsilon` of every component
      - :ref:`Exergy analysis examples <examples_exergy_analysis_label>`
    * - 2
      - :ref:`Component sizing <component_sizing_label>`, only where a cost is estimated from the size
      - the analysed plant; heat transfer coefficients for the heat exchangers
      - the size a cost function takes, for example power, heat transfer area or heat flow
      - :ref:`Purchased equipment costs <examples_purchase_costs_label>`
    * - 3
      - :ref:`Purchased equipment costs <purchase_equipment_costs_label>`
      - known costs, costs of reference components, user-defined cost equations or the correlations of
        `OpenPyTEA <https://github.com/pbtamarona/OpenPyTEA>`__
      - the purchased equipment cost of every component and its reference year
      - :ref:`Purchased equipment costs <examples_purchase_costs_label>`
    * - 4
      - :ref:`Economic analysis <economic_analysis_label>`
      - the purchased equipment costs; rate of return, lifetime, operating hours, fuel prices
      - the cost rate :math:`\dot{Z}` of every component and the levelized costs of the fuels
      - :ref:`From equipment costs to the cost of the product <examples_heatpump_exergoeconomic_label>`
    * - 5
      - :ref:`Exergoeconomic analysis <exergoeconomic_analysis_label>`
      - the results of steps 1 and 4
      - the cost of every stream; :math:`c_\mathrm{F}`, :math:`c_\mathrm{P}`,
        :math:`\dot{C}_\mathrm{D}`, :math:`f` and :math:`r` of every component
      - :ref:`Exergoeconomic analysis examples <examples_exergoeconomic_analysis_label>`

Steps 1 and 5 are enough where the cost rates :math:`\dot{Z}` are known; steps 2 to 4 obtain them
from the equipment costs.
