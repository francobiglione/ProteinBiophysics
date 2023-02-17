# -*- coding: utf-8 -*-
"""CD_library.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/17x0Ggu4TE4JErC10R3uxj5g-LsVmnQdx
"""

'''CD library to analyze protein CD data registered in JASCO J- series and saved as .csv files


Author: Franco Agustin Biglione, Biotechnologist. 
Biophysics of Molecular Recognition Laboratory. Institute of Molecular and Celular Biology of Rosario, Argetina.
National University of Rosario.

Contact: biglioneibr@gmail.com '''

import os
import sys
import csv
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

class cd_spectra(): 
  '''This class is to import a CD spectrum acquired in a JASCO spectropolarimeter and exported as CSV file

  Parameters
  ----------
  path: String. Path of the data file (.csv). The source file must have the colums XUNITS: NANOMETERS, YUNITS: CD [mdeg], Y2UNITS: HT [V].
  ht_max: Int. Value of the maximum permitted HT. This value will be used to filter non-reliabale data. The default value of None behaves like "ht_max = 600".
  abs: Bool. The source file contains an extra column Y3UNITS: ABSORBANCE. The default value of None behaves like "abs = False".

  Attributes
  ----------
  path: String. path of the imported spectrum file

  name: String. name of the imported spectrum file

  title: String. title set on when the experiment was ran

  info: DataFrame. Spectrum information stored in spectrum file by default.Contains tile and comments among others. 

  data: DataFrame containing the ellipticity, wavelenght and HT data 

  metadata: DataFrame. Metadata at the end of the spectrum file

  wavelength: Series. Recorded wavelengthsthis attribute is mutable and changes when applying some methods 

  ellipticity: Series. Recorded ellipticity, this attribute is mutable and changes when applying some methods

  wv_min: Float. Minumun registered wavelenght

  wv_max:  Float. Maximum registered wavelenght

  abs: Series. Recorded aborbance

  ht: Series. Recorded HT

  wv_delta: Float. Data pitch interval

  filtered: Bool. True if the data has already been filtered by the maximun allowed HT value

  corrected: Bool. True if the data has already been baseline corrected

  wv_cutoff: Float. Minimun allowed wavelength where HT< ht_max


  Methods
  --------

  ht_filter: filter the data according to ht_max and replaces the attributes ellipticity and wavelength 

  baseline: substract the specified baseline spectrum

  smooth: smooths the data using the Savitzky-Golay filter

  mre: calculates the Mean Residue Ellipticity and replaces the attribute ellipticity with the transformed values

  integrate: uses the Reimann's sum to approximate the absolute integral of a defined region '''  
    
    
  def __init__(self, path, ht_max = 600, abs = False):
    self.path = path
    self.name = os.path.basename(self.path)[:-4]
    
    self.cols = ['Wavelength [nm]', 'CD [mdeg]', 'HT [V]']
    
    if abs:
      self.cols = ['Wavelength [nm]', 'CD [mdeg]', 'HT [V]', 'Abs [UA]']
    
    with open(self.path) as rawdata: 
      file_csv = csv.reader(rawdata)
      for position, line in enumerate(file_csv):
          
          if position == 0: 
            self.title = line[0].split(';')[1] #Guardo el titulo del espectro] #Guardo el titulo del espectro
          elif "XYDATA" in line: 
              start = position+1 #Encuentro el número de linea donde empiezan los datos del espectro
          elif '##### Extended Information' in line:
              end = position-1 #Encuentro fin de los datos
              break
            
    self.info = pd.read_csv(self.path, delimiter = ';', names =['Information', 'Data'], nrows = start, decimal = ',' ).T
    self.info.columns = self.info.iloc[0] #Seteo los nombres de las columnas
    self.info.drop("Information",inplace=True) #Elimino la columna con nombres duplicados
            
    self.data = pd.read_csv(self.path, delimiter = ';', names =self.cols, header = start-1, 
                                      nrows = (end-start), decimal = ',' )
    
    self.metadata = pd.read_csv(self.path, delimiter = ';', names =['Metadata', 'Data'], header = end+1, decimal = ',' ).T #Creo dataframe con metadata y transpongo con .T
    self.metadata.columns = self.metadata.iloc[0].str.strip() #Seteo los nombres de las columnas y elimino los espacios vacios al principio o al final
    self.metadata.drop("Metadata",inplace=True)  #Elimino la columna con nombres duplicados
    
    #Creo data frame con los datos

    self.wavelength_raw = self.data['Wavelength [nm]']    
    self.wavelength = self.data['Wavelength [nm]'] #Creo atributo de la clase con longitudes de onda medidas
    self.ellipticity_raw = self.data['CD [mdeg]']
    self.ellipticity = self.data['CD [mdeg]'] #Creo atributo con elipticidades
    self.ht = self.data['HT [V]']    #Creo atributo con HT
    if abs:
      self.abs = self.data['Abs [UA]']

    self.wv_min = self.wavelength.iloc[-1]
    self.wv_max= self.wavelength.iloc[0]

    position_cutoff = len(self.wavelength)

    for position, ht in enumerate(self.data['HT [V]']): #por default considera que los valores de HT mayores a 600 no son confiables
      if ht>ht_max:
          position_cutoff= position
          break
    self.idx_cutoff = position_cutoff-1
    self.wv_cutoff = self.wavelength.iloc[self.idx_cutoff]
    self.filtered = False
    self.corrected = False
    self.wv_delta = float(self.metadata['Data pitch'][0].replace(' nm',''))

  def ht_filter(self):
    ''' Filters the ellipticity and wavelength values according to ht_max'''

    if not(self.filtered):
      self.ellipticity = self.ellipticity.iloc[:self.idx_cutoff+1]
      self.wavelength =  self.wavelength.iloc[:self.idx_cutoff+1]
      self.filtered = True
    
    else: 
      print('Your data has already been filtered using HT threshold')

  def baseline(self,baseline_path):
    '''Corrects the ellipticity values by substracting the baseline spectrum.
    
      Parameters
      ----------
      baseline_path: Path of the csv file containing the baseline spectrum

      Attributes
      ----------
      blank: DataFrame. DataFrame with registered ellipticity and HT values (and Absorbance if "abs =True") at each wavelength. 

    '''
    if not (self.corrected):
      with open(baseline_path) as rawdata: 
        data_baseline = csv.reader(rawdata)
        
        for position, line in enumerate(data_baseline):
            if "XYDATA" in line: 
                start= position+1 #Encuentro el número de linea donde empiezan los datos del espectro
            elif '##### Extended Information' in line:
                end = position-1 #Encuentro fin de los datos
                break #Una vez que encuentro el fin de los datos corto la iteración
            
      self.blank = pd.read_csv(baseline_path, delimiter = ';', names =self.cols, header = start-1, 
                                      nrows = (end-start), decimal = ',' )
      
      wv_min = self.wv_min
      
      if self.filtered:
        wv_min = self.wv_cutoff
      self.wavelength = self.blank['Wavelength [nm]'][(self.blank['Wavelength [nm]'] >= wv_min) & (self.blank['Wavelength [nm]'] <= self.wv_max)]
      self.ellipticity = self.ellipticity - self.blank['CD [mdeg]'][(self.blank['Wavelength [nm]'] >= wv_min) & (self.blank['Wavelength [nm]'] <= self.wv_max)]
      self.corrected = True

    else:
      print('Baseline is already corrected')

  def smooth (self, wdw, polyorder):
    '''Smooths the ellipticity values using the Savitzky-Golay filter.
    
      Parameters
      ----------
      wdw: data window 
      polyorder: order of the polynomial

    '''
    self.smoothed = savgol_filter(self.ellipticity, wdw, polyorder)

  def mre(self,concentration,aa_number = 1,pathlength=1):
    '''Calculates the mean ellipticity and replaces the ellipticity values
    
      Parameters
      ----------
      concentration: Float. protein molar concentration.
      aa_number:Int. if the ellipticity wants to be transformed to mean residue ellipticity the number of residues should be indicated. The default of None behaves like ``aa_number=1``
      pathlength: Float. Optical pathlength of the cell used to record the spectra. The default of None behaves like ``pathlength=1``
    '''
    self.ellipticity = self.ellipticity/(10*concentration*aa_number*pathlength)

  def integrate(self,wv_limit_lower,wv_limit_upper): #Define una suma de riemann
    ''' Approximates the absolute integral under the spectra by applying Riemann's sum. 
    
    Parameters
    ----------
    wv_limit_lower: Float. Lower integration window limit.
    wv_limit_upper: Float. Upper integration window limit.
   
    '''
    self.integral = self.wv_delta * self.ellipticity.iloc[self.wavelength[self.wavelength == wv_limit_upper].index[0]:self.wavelength[self.wavelength == wv_limit_lower].index[0]+1].sum()

class cd_melting_curve(): #Al llamar la clase debo pasarle el path del archivo .csv donde esta el espectro y HT cutoff
  '''This class is to import a CD melting curve acquired in a JASCO spectropolarimeter and exported as CSV file

  Parameters
  ----------
  path: String. Path of the data file (.csv). The source file must have the colums XUNITS: Temperature[C], YUNITS: CD [mdeg], Y2UNITS: HT [V].
  ht_max: Int. Value of the maximum permitted HT. This value will be used to filter non-reliabale data. The default value of None behaves like "ht_max = 600".
  abs: Bool. The source file contains an extra column Y3UNITS: ABSORBANCE. The default value of None behaves like "abs = False".

  Attributes
  ----------
  path: String. path of the imported spectrum file

  name: String. name of the imported spectrum file

  title: String. title set on when the experiment was ran

  info: DataFrame. Spectrum information stored in spectrum file by default.Contains tile and comments among others. 

  data: DataFrame containing the ellipticity, wavelenght and HT data 

  metadata: DataFrame. Metadata at the end of the spectrum file


  temperature: Series. Recorded temperatures.

  ellipticity: Series. Recorded ellipticity.

  temp_min: Float. Minumun registered wavelenght

  temp_max:  Float. Maximum registered wavelenght

  abs: Series. Recorded aborbance

  ht: Series. Recorded HT

  wv_monitor: Float. Wavelength at which each ellipticity signal was measured.

  

  Methods
  --------

  smooth: smooths the data using the Savitzky-Golay filter
 '''  
  
  
  
  
  
  def __init__(self, path, ht_max = 600, abs = False):
    self.path = path #Nombre con extensión .csv
    self.name = os.path.basename(self.path)[:-4] #Me deja el nombre del espectro quitandole la extensión csv
    
    self.cols = ['Temperature', 'CD [mdeg]', 'HT [V]']
    
    if abs:
      self.cols = ['Temperature', 'CD [mdeg]', 'HT [V]', 'Abs [UA]']
    
    with open(self.path) as rawdata: 
      file_csv = csv.reader(rawdata)
      for position, line in enumerate(file_csv):
          if position == 0: 
           self.title = line[0].split(';')[1] #Guardo el titulo del espectro] #Guardo el titulo del espectro
          elif "XYDATA" in line: 
            start = position+1 #Encuentro el número de linea donde empiezan los datos del espectro
          elif '##### Extended Information' in line:
            end = position-1 #Encuentro fin de los datos
            break
            
    self.info = pd.read_csv(self.path, delimiter = ';', names =['Information', 'Data'], nrows = start, decimal = ',' ).T
    self.info.columns = self.info.iloc[0] #Seteo los nombres de las columnas
    self.info.drop("Information",inplace=True) #Elimino la columna con nombres duplicados
            
    self.data = pd.read_csv(self.path, delimiter = ';', names =self.cols, header = start-1, 
                                      nrows = (end-start), decimal = ',' )
    
    self.metadata = pd.read_csv(self.path, delimiter = ';', names =['Metadata', 'Data'], header = end+1, decimal = ',' ).T #Creo dataframe con metadata y transpongo con .T
    self.metadata.columns = self.metadata.iloc[0].str.strip() #Seteo los nombres de las columnas y elimino los espacios vacios al principio o al final
    self.metadata.drop("Metadata",inplace=True)  #Elimino la columna con nombres duplicados
    
    #Creo data frame con los datos
        
    self.temperatures = self.data['Temperature'] #Creo atributo de la clase con longitudes de onda medidas
    self.ellipticity = self.data['CD [mdeg]'] #Creo atributo con elipticidades
    self.ht = self.data['HT [V]']    #Creo atributo con HT
    
    if abs:
      self.abs = self.data['Abs [UA]']

    self.temp_min = self.temperatures.iloc[-1]
    self.temp_max= self.temperatures.iloc[0]

    self.wv_monitor = float(self.metadata['Monitor wavelength'][0].replace(' nm',''))

  def smooth (self, wdw, polyorder):
    '''Smooths the ellipticity values using the Savitzky-Golay filter.
    
      Parameters
      ----------
      wdw: data window 
      polyorder: order of the polynomial

    '''
    self.smoothed = savgol_filter(self.ellipticity, wdw, polyorder)

class cd_melting_spectra(): #Al llamar la clase debo pasarle el path del archivo .csv donde esta el espectro y HT cutoff.
  '''This class is to import the CD spectra acquired in a JASCO spectropolarimeter in temperature interval mode and exported as CSV file

  Parameters
  ----------
  path: String. Path of the data file (.csv). The source file must have the colums XUNITS: NANOMETERS, YUNITS: CD [mdeg], Y2UNITS: HT [V].
  ht_max: Int. Value of the maximum permitted HT. This value will be used to filter non-reliabale data. The default value of None behaves like "ht_max = 600".
  abs: Bool. The source file contains an extra column Y3UNITS: ABSORBANCE. The default value of None behaves like "abs = False".

  Attributes
  ----------
  path: String. path of the imported spectrum file

  name: String. name of the imported spectrum file

  title: String. title set on when the experiment was ran

  info: DataFrame. Spectrum information stored in spectrum file by default.Contains tile and comments among others. 

  data: DataFrame containing the ellipticity, wavelenght, temperature and HT data 

  metadata: DataFrame. Metadata at the end of the spectrum file


  wavelength: Series. Recorded wavelengthsthis attribute is mutable and changes when applying some methods 

  temperatures: Series. Recorded temperatures.

  wv_delta: Float. Data pitch interval

  
  Methods
  --------

  smooth: smooths the data using the Savitzky-Golay filter

  mre: calculates the Mean Residue Ellipticity and replaces the attribute ellipticity with the transformed values

  integrate: uses the Reimann's sum to approximate the absolute integral of a defined region '''  
    
  
  
  def  __init__(self, path, ht_max = 600):
    self.path = path #Nombre con extensión
    self.name = os.path.basename(self.path)[:-4]
    with open(self.path) as rawdata: 
      data = csv.reader(rawdata)
      for position, line in enumerate(data):
          if 'TITLE' in line[0]: 
            self.title = line[0].split(';')[1] #Guardo el titulo del espectro
          elif 'Channel 1' in line: 
              start= position+1 #Encuentro el número de linea donde empiezan los datos de elipticidad
          elif 'Channel 2' in line:
              end = position-1 #Encuentro fin de los datos de elipticidad
              break #Una vez que encuentro el fin de los datos corto la iteración
          
      CD = pd.read_csv(self.path, delimiter = ';', header = start, nrows = (end-start), index_col = 0, decimal = ',' )
      HT = pd.read_csv(self.path, delimiter = ';', header = (end+2), index_col = 0, decimal = ',')

    self.info = pd.read_csv(self.path, delimiter = ';', names =['Information', 'Data'], nrows = start, decimal = ',' ).T
    self.info.columns = self.info.iloc[0] #Seteo los nombres de las columnas
    self.info.drop("Information",inplace=True) #Elimino la columna con nombres duplicados

    delta = self.info['DELTAX'][0]
    self.wv_delta = abs(float(delta.replace(',','.')))

    CD['Wavelength [nm]'] = list(CD.index.values)
    HT['Wavelength [nm]'] = list(HT.index.values)

    CD.columns = [value.replace(',','.') for value in CD.columns.values]
    HT.columns = [value.replace(',','.') for value in HT.columns.values]

    self.wavelength = list(CD.index.values) #Creo atributo de la clase con longitudes de onda medidas
    self.temperatures = list(CD.columns.values[:-1]) #Extraigo nombre de las columnas

    CD = CD.melt(id_vars ='Wavelength [nm]', var_name='Temperature', value_name='CD_raw [mdeg]')
    HT = HT.melt(id_vars ='Wavelength [nm]',var_name='Temperature', value_name='HT [V]')

    data = pd.merge(CD,HT['HT [V]'],left_index=True,right_index=True)
    data['CD_filtered [mdeg]'] = np.nan

    data['CD_filtered [mdeg]'][data['HT [V]'] <= ht_max] = data['CD_raw [mdeg]'][data['HT [V]'] <= ht_max]
    
    self.data = data
    self.mre_transformation = False

  def mre(self,concentration,aa_number = 1,pathlength=1):
    '''Calculates the mean ellipticity and stores it in the data attribute
    
      Parameters
      ----------
      concentration: Float. protein molar concentration.
      aa_number:Int. if the ellipticity wants to be transformed to mean residue ellipticity the number of residues should be indicated. The default of None behaves like ``aa_number=1``
      pathlength: Float. Optical pathlength of the cell used to record the spectra. The default of None behaves like ``pathlength=1``
    '''
    self.data['CD_mre [deg.cm2.dmol-1]'] = self.data['CD_filtered [mdeg]']/(10*concentration*aa_number*pathlength)
    self.mre_transformation = True
  
  def smooth(self,wdw, polyorder):
    '''Smooths the ellipticity values using the Savitzky-Golay filter and stores it in the data attribute
    
      Parameters
      ----------
      wdw: data window 
      polyorder: order of the polynomial

    '''
    column = 'CD_filtered [mdeg]'

    if self.mre_transformation:
      column = 'CD_mre [deg.cm2.dmol-1]'
    
    self.data['CD_smoothed [mdeg]'] = savgol_filter(self.data[column], wdw, polyorder)
  
  def integrate(self,wv_limit_lower,wv_limit_upper): #Define una suma de riemann
    ''' Approximates the absolute integral under the spectra by applying Riemann's sum. The result is a list of integrals in the same order as the attribute temperatures.
    
    Parameters
    ----------
    wv_limit_lower: Float. Lower integration window limit.
    wv_limit_upper: Float. Upper integration window limit.
   
    '''
    column = 'CD_filtered [mdeg]'

    if self.mre_transformation:
      column = 'CD_mre [deg.cm2.dmol-1]'
    integrals = []
    for temperature in self.temperatures:
      integrals.append(self.wv_delta * self.data[column][(self.data['Temperature'] == temperature) & (self.data['Wavelength [nm]'] <= wv_limit_upper) & (self.data['Wavelength [nm]'] >= wv_limit_lower)].sum())
    
    self.integrals = integrals
