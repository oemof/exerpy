from win32com.client import Dispatch
import sys
import os

def doSimulate():
    MODELPATH = 'C:/Users/sergiotomasinelli/Desktop/exerpy/tests/simple_test.ebs'

    # 1. Start the EBSILON application
    app = Dispatch("EbsOpen.Application")
    
    # 2. Open the EBSILON model
    model = app.Open(MODELPATH)
    oc = app.ObjectCaster

    # 3. Perform simulation and collect errors
    calc_errors = model.CalculationErrors
    model.Simulate(calc_errors)
    print("Simulation has " + str(calc_errors.Count) + " errors")

    # 4. Create variables for components of the model and access their data
    Compressor = oc.CastToComp24(model.Objects.Item('AC'))
    CombustionChamber = oc.CastToComp22(model.Objects.Item('CC'))
    Turbine = oc.CastToComp23(model.Objects.Item('EXP'))
    print('m_1 = %.2f kg/s' % (Compressor.M1N.Value))


    # 5. Create variables for connections of the model and access their data
    stream2 = oc.CastToPipe(model.Objects.Item('2'))
    print('T_2 = %.2f °C' % (stream2.T.Value))

    # 6. Access the fluid properties for a simple substance
    # Add now (why?) the directory containing EbsOpen.py to the system path
    sys.path.append(r"C:\Program Files\Ebsilon\EBSILONProfessional 17\Data\Python")

    # Now you can import the required components from EbsOpen
    from EbsOpen import EpFluidType, EpSteamTable, EpGasTable, EpSubstance
    
    fd = app.NewFluidData()
    fd.FluidType = EpFluidType.epFluidTypeSteam              # steam
    fd.SteamTable = EpSteamTable.epSteamTableIAPWS_IF97      # IF97 steamtable
 
    p = 100.0
    T = 500.0
    s = fd.PropertyS_OF_PT(p,T)
    print ('steam: p = %.3f bar, T = %.3f °C, s = %.6f kJ/kg/K' %(p,T,s))
 
    # 7. Create a mixture and access its fluid properties
    fd.FluidType = EpFluidType.epFluidTypeFluegas           # fluegas
    fd.GasTable = EpGasTable.epGasTableFDBR                 # FDBR table   
    fdAnalysis = app.NewFluidAnalysis()
    fdAnalysis.SetSubstance(EpSubstance.epSubstanceN2,0.7)  # N2 0.7 mass fraction
    fdAnalysis.SetSubstance(EpSubstance.epSubstanceO2,0.2)  # O2 0.2 mass fraction
    fdAnalysis.SetSubstance(EpSubstance.epSubstanceCO2,0.1) # CO2 0.1 mass fraction
    fd.SetAnalysis(fdAnalysis)
 
    p = 1.0
    T = 150.0
    s = fd.PropertyS_OF_PT(p,T)
    print ('fluegas: p = %.3f bar, T = %.3f °C, s = %.6f kJ/kg/K' %(p,T,s))

'''    # 8. Get the entire composition of all streams and use it to calculate the entropy at ambient conditions
    p_0 = 1.013  # Ambient pressure in bar
    T_0 = 15  # Ambient temperature in °C
    
    # Create a list of all streams
    streams = [stream1, stream2, stream3, stream4, stream5, stream6, stream7, stream8]

    # Loop over all streams and calculate entropy
    for i, stream in enumerate(streams, start=1):
        entropy = calc_X_from_PT(app, stream, "S", p_0, T_0)
        print(f"Stream {i} entropy: s = {entropy:.6f} kJ/kg/K at ambient p = {p_0:.3f} bar and T = {T_0:.3f} °C")

    # Loop over all streams and calculate entropy
    for i, stream in enumerate(streams, start=1):
        entropy = calc_X_from_PT(app, stream, "H", p_0, T_0)
        print(f"Stream {i} enhtalpy: s = {entropy:.6f} kJ/kg at ambient p = {p_0:.3f} bar and T = {T_0:.3f} °C")'''
 
# Main program
doSimulate()
exit()
