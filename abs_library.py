# -*- coding: utf-8 -*-
"""abs_library.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1KLkiXYg7NRowgjey4stznoHC22NeLcMK
"""

import os
import sys
import csv
import pandas as pd
import numpy as np
from scipy.signal import

class abs_spectra(): 
  '''This class is to import an Absorbance spectrum acquired in a JASCO spectrophotometer and exported as CSV file.

  Parameters
  ----------
  path: String. Path of the data file (.csv). The source file must have the colums XUNITS: NANOMETERS, YUNITS: ABSORBANCE.
 
  Attributes
  ----------
  path: String. path of the imported spectrum file
  name: String. name of the imported spectrum file
  title: String. title set on when the experiment was ran
  info: DataFrame. Spectrum information stored in spectrum file by default.Contains tile and comments among others. 
  metadata: DataFrame. Metadata at the end of the spectrum file
  wavelength: Series. Recorded wavelengths
  absorbance: Series. Recorded absorbance, this attribute is mutable and changes when applying some methods
  wv_min: Float. Minumun registered wavelenght
  wv_max:  Float. Maximum registered wavelenght
  wv_delta: Float. Data pitch interval
  corrected: Bool. True if the data has already been baseline corrected
  concentration: Float. Gives the molar concentration calculated using the absorbance at a fixed wavelength, molar extinction coefficient and pathlength.
  Methods
  --------
  
  baseline: substract the specified baseline spectrum and also allows the substraction of a fixed absorbance value at a certain wavelength
  smooth: smooths the data using the Savitzky-Golay filter
  concentration_calc: calculates the molar concentration using a given molar extinction coefficient and pathlength
  integrate: uses the Reimann's sum to approximate the absolute integral of a defined region '''  
    
    
  def __init__(self, path):
    self.path = path
    self.name = os.path.basename(self.path)[:-4]
    
    self.cols = ['Wavelength [nm]', 'Abs [UA]']
    
 
    with open(self.path) as rawdata: 
      file_csv = csv.reader(rawdata)
      for position, line in enumerate(file_csv):
          
          if position == 0: 
            self.title = line[0].split(';')[1] #Saves the title of the spectra
          elif "XYDATA" in line: 
              start = position+1 #Find the first line with spectral data
          elif '##### Extended Information' in line:
              end = position-1 #Encuentro fin de los datos
              break
            
    self.info = pd.read_csv(self.path, delimiter = ';', names =['Information', 'Data'], nrows = start, decimal = ',' ).T
    self.info.columns = self.info.iloc[0] #Set columns names
    self.info.drop("Information",inplace=True) #Erase duplicated columns
            
    self.data = pd.read_csv(self.path, delimiter = ';', names =self.cols, header = start-1, 
                                      nrows = (end-start), decimal = ',' )
    
    self.metadata = pd.read_csv(self.path, delimiter = ';', names =['Metadata', 'Data'], header = end+1, decimal = ',' ).T #Create and transpose dataframe with metadata
    self.metadata.columns = self.metadata.iloc[0].str.strip() #Set column names and delete whitespaces
    self.metadata.drop("Metadata",inplace=True)  #Erase duplicated columns
    

    self.wavelength = self.data['Wavelength [nm]'] 
    self.abs_raw = self.data['Abs [UA]']
    self.abs = self.data['Abs [UA]']
    self.wv_min = self.wavelength.iloc[-1]
    self.wv_max= self.wavelength.iloc[0]

    self.corrected = False
    self.wv_delta = float(self.metadata['Data pitch'][0].replace(' nm',''))

 
  def baseline(self,baseline_path = None, nm = None):
    '''Corrects the absorbance values by substracting the baseline spectrum.
    
      Parameters
      ----------
      baseline_path: Path of the csv file containing the baseline spectrum
      Attributes
      ----------
      blank: DataFrame. DataFrame with registered absorbance and HT values (and Absorbance if "abs =True") at each wavelength. 
    '''
    if not baseline_path:
      if not (self.corrected):
        with open(baseline_path) as rawdata: 
          data_baseline = csv.reader(rawdata)
          
          for position, line in enumerate(data_baseline):
              if "XYDATA" in line: 
                  start= position+1 
              elif '##### Extended Information' in line:
                  end = position-1 
                  break 
              
        self.blank = pd.read_csv(baseline_path, delimiter = ';', names =self.cols, header = start-1, 
                                        nrows = (end-start), decimal = ',' )
        
        self.abs = self.abs - self.blank['Abs [UA]']
        self.corrected = True
      else:
        print('You have already substracted the buffer!')
    

    if not nm:
      idx = self.nm[self.wavelength == nm].index
      self.abs = self.abs - self.abs[idx]
    else:
      print('You have already substracted a baseline value!')

  def smooth (self, wdw, polyorder):
    '''Smooths the absorbance values using the Savitzky-Golay filter.
    
      Parameters
      ----------
      wdw: data window 
      polyorder: order of the polynomial
    '''
    self.smoothed = savgol_filter(self.abs, wdw, polyorder)

  def concentration_calc (self, wv, molar_extinction_coeff, pathlength):
    '''Calculates the concentration of the molecule using its molar extinction coefficient at a fixed wavelength and the optical pathlenght.
    
      Parameters
      ----------
      wv: wavelength of the molar extinction coefficient 
      molar_extinction_coeff: Molar extinction coefficient in M^-1*cm^-1
      pathlenght: cm
      '''
    idx = self.nm[self.wavelength == wv].index
    abs = self.abs - self.abs[idx]
    self.concentration = abs/(molar_extinction_coeff*pathlength)

  def integrate(self,wv_limit_lower,wv_limit_upper): #Define una suma de riemann
    ''' Approximates the absolute integral under the spectra by applying Riemann's sum. 
    
    Parameters
    ----------
    wv_limit_lower: Float. Lower integration window limit.
    wv_limit_upper: Float. Upper integration window limit.
   
    '''
    self.integral = self.wv_delta * self.abs.iloc[self.wavelength[self.wavelength == wv_limit_upper].index[0]:self.wavelength[self.wavelength == wv_limit_lower].index[0]+1].sum()