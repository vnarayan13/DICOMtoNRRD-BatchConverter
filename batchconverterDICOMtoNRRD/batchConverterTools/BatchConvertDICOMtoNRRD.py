from __future__ import print_function

from __main__ import vtk, qt, ctk, slicer
import os
import glob
from datetime import datetime

import SimpleITK as sitk
import sitkUtils as su

import pdb

from BatchRTStructConversion import BatchRTStructConversionLogic
from DatabaseHandler import DatabaseHandler

def SaveVolumes(listVolumes, outputReconstructionsDir, fileFormat, logFilePath):
    volumesLogic = slicer.vtkSlicerVolumesLogic()
    for volume in listVolumes:     
        volumesLogic.CenterVolume(volume)
        savename = volume.GetName() 
        savename = ''.join(x for x in savename if x not in "',;\/:*?<>|") + fileFormat       
        savevol = slicer.util.saveNode(volume, os.path.join(outputReconstructionsDir, savename), properties={"filetype": fileFormat})
        if not savevol:
            with open(logFilePath,mode='a') as logfile: logfile.write("\tSAVEERROR: Could not save data" + volume.GetName() + '\n') 

def VolumeIntensityCorrection(volume, logFilePath):
    spacing = volume.GetSpacing()
    origin = volume.GetOrigin()
    ras2ijk = vtk.vtkMatrix4x4()
    ijk2ras = vtk.vtkMatrix4x4()
    volume.GetRASToIJKMatrix(ras2ijk)
    volume.GetIJKToRASMatrix(ijk2ras)
    
    imgsitk = su.PullFromSlicer(volume.GetName())
    imgsitk_array = sitk.GetArrayFromImage(imgsitk)
    imgsitk_array = imgsitk_array.__sub__(imgsitk_array.min())
    imgsitk = sitk.GetImageFromArray(imgsitk_array)
    outputImageName = volume.GetName() + '_corrected'
    su.PushToSlicer(imgsitk, outputImageName)
    volumeCorrected = slicer.util.getNode(outputImageName)
          
    volumeCorrected.SetOrigin(origin)
    volumeCorrected.SetSpacing(spacing)
    volumeCorrected.SetRASToIJKMatrix(ras2ijk)
    volumeCorrected.SetIJKToRASMatrix(ijk2ras)
    
    with open(logFilePath,mode='a') as logfile: logfile.write("\tCORRECTED: Image intensity values corrected: " + volumeCorrected.GetName() + '\n')
    return volumeCorrected
  
def InitializeProgressBar(numDirectories):
    # initialize Progress Bar
    progressBar = qt.QProgressDialog(slicer.util.mainWindow())
    progressBar.minimumDuration = 0
    progressBar.show()
    progressBar.setValue(0)
    progressBar.setMaximum(numDirectories)
    return progressBar
  
def UpdateProgressBar(progressBar, patientID, index):
    progressBar.labelText = 'Converting DICOM Images to NRRD for patient: %s ' % patientID
    progressBar.setValue(index)
    slicer.app.processEvents()
 
def batchConvert(inputPatientDir, outputPatientDir, fileFormat):
    logTime = str(datetime.now().strftime(('%Y-%m-%d--%H-%M')))
    logFilePath = os.path.join(outputPatientDir, 'BatchConverterLog_' + logTime + '.txt')
    
    PatientDirs = [patDir for patDir in glob.glob(os.path.join(inputPatientDir, '*')) if os.path.isdir(patDir)]
    
    dblogic = DatabaseHandler(inputPatientDir)
    RTStructConversionlogic = BatchRTStructConversionLogic()   
    progressBar = InitializeProgressBar(len(PatientDirs))
    
    for index,patientDir in enumerate(PatientDirs):
        patientDirName = os.path.basename(patientDir) 
        UpdateProgressBar(progressBar, patientDirName, index)              
        with open(logFilePath,mode='a') as logfile: logfile.write("\nPROCESSING: " + patientDirName)
        
        # Import Directory into ctkDICOMIndexer. If that fails, instantiate a new database file
        # Check if import added any new patients to the database
        try:
            patientsAdded = dblogic.ImportStudy(patientDir)
        except:
            dblogic.SetAndOpenNewDatabase()
            patientsAdded = dblogic.ImportStudy(patientDir)       
        if patientsAdded == 0:    
            with open(logFilePath,mode='a') as logfile: logfile.write("\tPATIENTERROR: No new patients added to database from directory: " + patientDirName)
            slicer.mrmlScene.Clear(0)
            continue
        
        detailsPopup = slicer.modules.dicom.widgetRepresentation().self().detailsPopup
        for patient in patientsAdded:
            try:    
                studiesList = slicer.dicomDatabase.studiesForPatient(patient)
            except:
                with open(logFilePath,mode='a') as logfile: logfile.write("\tSTUDYERROR: could not find studies for Patient: " + patientDirName + ' with DB Index: ' + patient)
                slicer.mrmlScene.Clear(0)
                continue
                      
            for study in studiesList:
                try:    
                    seriesListStudy = slicer.dicomDatabase.seriesForStudy(study)
                except:
                    with open(logFilePath,mode='a') as logfile: logfile.write("\tSERIESERROR: could not find Series for Study: " + study + " for Patient: " + patientDirName)
                    slicer.mrmlScene.Clear(0)
                    continue
                
                # Create Output Patient Directory
                try: patientID = str(dblogic.GetDicomHeaderAttribute(seriesListStudy[0],'0010,0020'))
                except: patientID = patientDirName
                outputPatientDir = str(os.path.join(outputPatientDir,patientID))
                if not os.path.exists(outputPatientDir): os.mkdir(outputPatientDir)
                #else: # check if output has already been saved to folder
                #    with open(logFilePath,mode='a') as logfile: logfile.write('\tSKIPPING: ' + patientDirName + ' with ID: ' + patientID)
                #    slicer.mrmlScene.Clear(0)
                #    continue  
                
                # Create Output Study Directory Within Patient Directory
                try: studyDate = dblogic.GetDicomHeaderAttribute(seriesListStudy[0], '0008,0020')
                except: studyDate = "Unknown-" + str(datetime.now().strftime(('%Y-%m-%d--%H-%M')))
                try: studyDescription = dblogic.GetDicomHeaderAttribute(seriesListStudy[0], '0008,1030')
                except: studyDescription = "Unknown"    
                studyDateDirName = studyDate + '_' + studyDescription
                studyDateDirName = ''.join(x for x in studyDateDirName if x not in "-',;\/:*?<>|")         
                outputStudyDateDir = str(os.path.join(patientDir,studyDateDirName))      
                if not os.path.exists(outputStudyDateDir): os.mkdir(outputStudyDateDir)
                
                # Create Reconstructions, Segmentations, and Resources Directories
                outputReconstructionsDir = os.path.join(outputStudyDateDir, 'Reconstructions')
                outputSegmentationsDir = os.path.join(outputStudyDateDir, 'Segmentations')
                outputResourcesDir = os.path.join(outputStudyDateDir, 'Resources')
                if not os.path.exists(outputReconstructionsDir): os.mkdir(outputReconstructionsDir)
                if not os.path.exists(outputSegmentationsDir): os.mkdir(outputSegmentationsDir) 
                if not os.path.exists(outputResourcesDir): os.mkdir(outputResourcesDir)

                """
                ###BRAINLAB####
                lstdates = {}
                for volume in listVolumes:
                  if 'FLAIR' not in volume.GetName().upper():           
                    seriesDate = dblogic.GetDicomHeaderAttributeLoaded(volume,'0008,0021')
                    lstdates[seriesDate] = volume
                if min(lstdates.keys()) != max(lstdates.keys()):
                  if '_preop' not in lstdates[min(lstdates.keys())].GetName():          
                    lstdates[min(lstdates.keys())].SetName( lstdates[min(lstdates.keys())].GetName() + '_preop' )
                  if '_postop' not in lstdates[max(lstdates.keys())].GetName():  
                    lstdates[max(lstdates.keys())].SetName( lstdates[max(lstdates.keys())].GetName() + '_postop' )
                else:
                  contourNodes = slicer.util.getNodes('vtkMRMLContourNode*').values()
                  for contourNode in contourNodes.values():
                    if 'POST' in contourNode.GetName().upper():
                      if '_preop' not in lstdates[min(lstdates.keys())].GetName(): 
                        lstdates[max(lstdates.keys())].SetName( lstdates[max(lstdates.keys())].GetName() + '_postop' )
                    else:
                      if '_postop' not in lstdates[max(lstdates.keys())].GetName():
                        lstdates[min(lstdates.keys())].SetName( lstdates[min(lstdates.keys())].GetName() + '_preop' )
                ################ 
                """
                
                ### Load Images from Study into Slicer
                listVolumes = dblogic.LoadPatientsIntoSlicer(study)          
                if not listVolumes: 
                    with open(logFilePath, mode='a') as logfile: logfile.write("\tIMAGEERROR: could not Parse Images: " + patientDirName + ', study: ' + studyDate)     
                # Perform intensity correction on images and save them         
                # listVolumes = [VolumeIntensityCorrection(volume, logFilePath=logFilePath) if volume.GetImageData().GetScalarRange()[0] > 32000.0 else volume for volume in listVolumes]      
                SaveVolumes(listVolumes, outputReconstructionsDir, fileFormat, logFilePath)
                
                # Get label map contours         
                listLabelMapContours = RTStructConversionlogic.ConvertContoursToLabelmap(listVolumes, logFilePath)                  
                if len(listLabelMapContours) > 0:                 
                    RTStructConversionlogic.SaveLabelMapContours(listLabelMapContours, outputSegmentationsDir, fileFormat, logFilePath)            
                else:
                    with open(logFilePath,mode='a') as logfile: logfile.write("\tRTSTRUCTERROR: could not Parse RTSTRUCTs: " + patientDirName + ', study: ' + studyDate)  
                
                # Clear data within Slicer
                slicer.mrmlScene.Clear(0)
            slicer.mrmlScene.Clear(0)    
        slicer.mrmlScene.Clear(0)         
    slicer.mrmlScene.Clear(0)
    self.progressBar.close()
    self.progressBar = None