---
title: 'ExerPy: An open-source framework for automated exergy analysis'
tags:
  - Python
  - exergy analysis
  - exergy-based methods
  - applied thermodynamics
authors:
  - name: Sergio Tomasinelli
    corresponding: true
    orcid: 0009-0002-5084-436X
    affiliation: 1
  - name: Francesco Witte
    orcid: 0000-0003-4019-0390
    affiliation: 2
  - name: Robert Müller
    orcid: 0000-0002-2035-4530
    affiliation: 1
  - name: Fontina Petrakopoulou
    orcid: 0000-0001-6878-4591
    affiliation: 1
affiliations:
 - name: Chair of Energy Engineering and Climate Protection, Technische Universität Berlin, Germany
   index: 1
 - name: Institute of Networked Energy Systems, German Aerospace Center (DLR), Germany
   index: 2
date: 22 July 2025
bibliography: paper.bib

---

# Summary

ExerPy is an open-source Python framework that automates exergy analysis of thermodynamic systems. It integrates with established simulation envirnoments, such as Aspen Plus®, Ebsilon Professional®, and TESPy, via a unified JSON interface. ExerPy automatically identifies components and defines component- and system-level exergy balances. It also outputs metrics, such as exergy destruction and exergetic efficiency. By handling both physical and chemical exergy and reducing the need for manual calculations, ExerPy enables consistent second-law assessments for a wide range of systems, from simple cycles to complex plants. ExerPy facilitates the integration of analysis across tools and enables the subsequent processing of data through the use of standardized outputs.

# Statement of need

Exergy analysis is an effective tool for assessing the quality of energy and the capacity to generate work. It facilitates the identification of thermodynamic irreversibilities within a system, thereby offering a more comprehensive understanding of the energy conversion process. The quantification of exergy destruction enables researchers and engineers to develop strategies aimed at enhancing efficiency, reducing costs, and promoting sustainable conversion technologies [@Tsatsaronis_1993; @Meyer_2008; @petrakopoulou2017improving].

Despite its advantages, exergy analysis is not yet widely integrated into most
commercial software used for thermodynamic assessments, which focus on energy
and mass balance calculations. The calculation of both physical and chemical exergy of material streams as well as an automated evaluation of the overall process was seamlessly integrated into the open-source software TESPy
[@Witte_2020; @Witte_2022; @Hofmann2022]. While this was an important step in
facilitating the application of exergy analysis, exergy analysis efforts still
rely heavily on user input, are prone to incorrect interpretation of component
balances, and lack interoperability with other open source or commercially
available tools. These shortcomings have driven the demand for specialized,
user-friendly, automated open-source software that enables exergy-based
analyses and interoperates with both commercial and open-source tools.

To address these needs ExerPy provides a Python-based solution that automates
exergy analysis of energy-conversion systems via a JSON data interface. The
tool includes an API that automatically connects to Aspen Plus®, Ebsilon
Professional®, or TESPy, autonomously identifies components and assigns exergy
balances, enabling the detailed and accurate exergy analysis across the entire
process. This level of automation streamlines the workflow, improving
efficiency and accuracy in applying exergy analysis, and therefore supports the
optimization of energy-conversion systems from an exergy perspective.

# Features

ExerPy is divided into two main modules: the data processing module, which manages the extraction and preparation of simulation data, and the exergy analysis module, which conducts the detailed exergy calculations. The initial implementation supports Ebsilon Professional®, Aspen Plus®, and TESPy. The
architecture is outlined in the following sections and is shown in
\autoref{fig:structure}.

![Structure of the ExerPy framework.\label{fig:structure}](exerpy_vertical.svg){width="80%"}

## Data processing

A workflow starts with the parsing of simulation data from models created in
Ebsilon Professional®, Aspen Plus®, or TESPy, using the respective functions:
`from_ebsilon`, `from_aspen`, and `from_tespy`. It is important to note that
the physical exergy, calculated from the entropy and enthalpy of the streams,
is parsed directly from the simulation tools. Independent of the simulation
software, users also have the option to supply their own JSON file using
`from_json`, which must conform to the required format for exergy analysis.

During the parsing process, connection data such as mass flow ($m$),
temperature ($T$), pressure ($p$), enthalpy ($h$), entropy ($s$), and physical
exergy ($e^\text{PH}$) are parsed, along with the identification of target and
source components. In addition, component data including efficiency, energy
flows, and other relevant thermodynamic properties are also extracted. Ambient
conditions are taken directly from the simulation, or they can be specified by
the user manually.

ExerPy also allows splitting the physical exergy into thermal ($e^\text{T}$)
and mechanical ($e^\text{M}$) parts. This separation enables a more
comprehensive analysis of thermodynamic processes, especially for components
operating below ambient temperature [@morosuk2019splitting]. These values are
calculated using the native property functions of the simulation tools. In the
initial release of ExerPy, this separation is not yet available in Aspen Plus®
due to limited access to thermodynamic functions, but it is planned for a
future update.

After the data parsing is complete, chemical exergyis calculated from stream composition following TESPy’s approach [@Hofmann2022] and the reference environment developed by Ahrendts [@Ahrendts_1977]. For pure substances, values come from tabulated data in the selected thermodynamic model. For mixtures (e.g., air, flue gas), ExerPy computes specific chemical exergy from constituent molar fractions using standard assumptions (ideal behavior for gas mixtures, with adjustments for condensables such as water). Finally, all parsed and calculated data are consolidated into a standardized JSON file, independent of the simulation tool used, which includes all the necessary information for a comprehensive exergy analysis.

## Exergy Analysis

The framework performs exergy analysis at both the component and system levels.
Each component of the system—such as turbines, compressors, and heat
exchangers—is represented by a Python class that automatically assigns the
exergy of the fuel and exergy of the product of the component. Using these
definitions, ExerPy calculates relevant metrics for each component (i.e., the
exergy destruction and exergetic efficiency). Thermal energy losses of components are included in their exergy destruction, and streams discharged to the environment are considered exergy losses of the overall system. This
offers coherent calculations of  inefficiencies of each individual component
and enables targeted optimization

At the system level, the total exergy balance is determined by evaluating the
exergy of streams crossing the system boundaries. To perform this analysis, and
in the current release of the tool, it is necessary for the user to define the
product, the fuel, and the exergy loss of the overall process. The system-level
exergy analysis yields the overall exergetic efficiency and the total exergy
destruction of the overall system. Finally, the framework offers the
possibility to export the results as CSV files for further examination and
integration into additional workflows.

## Validation

Validation has been carried out based on three different case studies
documented in the online documentation of the framework [@exerpy-web].
The results of the exergy analysis of a combined cycle power plant simulated
with Aspen Plus® and with TESPy show a maximum difference of 1% compared to the
simulation results from Ebsilon Professional®, validating the accuracy and
confirming the flexibility of the tool. Additional applications and validation
of ExerPy, e.g. the CGAM process [@valero1994cgam] and a heat pump, are also
available in the documentation and GitHub repository.

# Acknowledgements

Parts of this work have been funded by the German Federal Ministry for Economic
Affairs and Climate Action through the research project SecöndLife, grant
number 03EI1076A.

# References
