from __main__ import vtk, qt, ctk, slicer, os

import batchConverterTools

#
# DICOM to NRRD Batch Converter module
#

class batchConverter:
    def __init__(self, parent):  
        parent.title = "DICOMBatchConverter"
        parent.categories = ["Converters"]
        parent.contributors = ["Vivek Narayan / Hugo Aerts"]
        parent.helpText = """
        This Module requires Slicer 4.4 and the DICOM-RT module installed.
        Use this module to convert DICOM/DICOM-RT files to NRRD images/label-maps in the following Data Hierarchy:
        --Dataset
            --PatientID
                --StudyDate_StudyDescription
                   --Reconstructions (Images)
                   --Resources
                   --Segmentations (Label-maps)
        """
        parent.acknowledgementText = """ This module was created at Dana Farber Cancer Institute""" 
        self.parent = parent

#
# Widget
#

class batchConverterWidget:
    def __init__(self, parent=None):
        if not parent:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
        else:
            self.parent = parent
        self.layout = self.parent.layout()
        if not parent:
            self.setup()
            self.parent.show()
    
        self.inputPatientDir = self.outputPatientDir = {}
        self.converterSettings = {}
        self.converterSettings['convertcontours'] = 'None'
        self.converterSettings["fileformat"] = ".nrrd"
        self.converterSettings["inferpatientid"] = "metadata"
        self.converterSettings["centerimages"] = False
        self.converterSettings["centerlabels"] = False
        
    def setup(self):    
        #---------------------------------------------------------
        # Batch Covert DICOM to NRRD
        self.BatchConvertCollapsibleButton = ctk.ctkCollapsibleButton()
        self.BatchConvertCollapsibleButton.text = "Batch convert DICOM to NRRD or NIFTI"
        self.layout.addWidget(self.BatchConvertCollapsibleButton)
        self.BatchConvertCollapsibleButton.collapsed = False 
        self.BatchConvertFormLayout = qt.QFormLayout(self.BatchConvertCollapsibleButton)
    
        # Input 1: Input Directory selector
        self.input1Selector = qt.QLabel("Input Directory (DICOM):  ", self.BatchConvertCollapsibleButton)
        self.input1Button = qt.QPushButton("Select Main Input Directory of DICOM files")
        self.input1Button.toolTip = "Select main directory with DICOM files (folder names are patient names)"
        self.input1Button.enabled = True
        self.BatchConvertFormLayout.addRow(self.input1Selector, self.input1Button)
    
        # Input 2: Output Directory selector       
        self.input2Selector = qt.QLabel("Output Directory:  ", self.BatchConvertCollapsibleButton)
        self.input2Button = qt.QPushButton("Select Main Output Directory")
        self.input2Button.toolTip = "Select main directory for output NRRD or NIFTI files (folder names are patient names)"
        self.input2Button.enabled = True
        self.BatchConvertFormLayout.addRow(self.input2Selector, self.input2Button)
        
        # RTStruct Conversion
        self.contourConvertLabel = qt.QLabel("Convert DICOM-RT Contours:  ", self.BatchConvertCollapsibleButton)
        
        self.contourConvertSelectFrame = qt.QFrame(self.BatchConvertCollapsibleButton)
        self.contourConvertSelectFrame.setLayout(qt.QHBoxLayout())
        self.contourConvertGroup = qt.QButtonGroup(self.contourConvertSelectFrame)
        self.noConvertButton = qt.QRadioButton("None")
        self.noConvertButton.checked = True
        self.allConvertButton = qt.QRadioButton("All")
        self.selectConvertButton = qt.QRadioButton("Select")
        self.contourConvertGroup.addButton(self.noConvertButton)
        self.contourConvertGroup.addButton(self.allConvertButton)
        self.contourConvertGroup.addButton(self.selectConvertButton)
        self.contourConvertSelectFrame.layout().addWidget(self.noConvertButton)
        self.contourConvertSelectFrame.layout().addWidget(self.allConvertButton)
        self.contourConvertSelectFrame.layout().addWidget(self.selectConvertButton)
        self.BatchConvertFormLayout.layout().addRow(self.contourConvertLabel, self.contourConvertSelectFrame)
        
        self.contourConvertCollapsibleButton = ctk.ctkCollapsibleButton(self.BatchConvertCollapsibleButton)
        self.contourConvertCollapsibleButton.text = "Select Contours to Convert"
        self.BatchConvertFormLayout.addRow(self.contourConvertCollapsibleButton)
        self.contourConvertCollapsibleButton.enabled = False 
        self.contourConvertCollapsibleButton.collapsed = True 
        self.contourConvertFormLayout = qt.QFormLayout(self.contourConvertCollapsibleButton)
        
        # Keywords to catch RTStruct Structures
        self.contoursFrame = qt.QFrame(self.contourConvertCollapsibleButton)
        self.contoursFrame.setLayout(qt.QVBoxLayout())
        self.contoursFrame.setFrameStyle(2)
        self.contourConvertFormLayout.addWidget(self.contoursFrame)
        
        self.addContourButton = qt.QPushButton("Add Contour to convert from RTStruct (separate keywords by comma)", self.contoursFrame)      
        self.keywordsScrollWidget = qt.QWidget()        
        self.keywordsScrollWidget.setLayout(qt.QFormLayout())        
        self.keywordsScroll = qt.QScrollArea()
        self.keywordsScroll.setWidgetResizable(True)
        self.keywordsScroll.setWidget(self.keywordsScrollWidget)        
        self.contoursFrame.layout().addWidget(self.keywordsScroll)
        self.contoursFrame.layout().addWidget(self.addContourButton) 
               
        # Settings Collapsible Button
        self.settingsCollapsibleButton = ctk.ctkCollapsibleButton()
        self.settingsCollapsibleButton.text = "Settings"
        self.settingsCollapsibleButton.setLayout(qt.QFormLayout())     
        self.layout.addWidget(self.settingsCollapsibleButton)
        
        # NRRD or NIFTI Radio Buttons
        self.fileFormatLabel = qt.QLabel("Output File Format:  ", self.settingsCollapsibleButton)
        
        self.fileFormatSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.fileFormatSelectFrame.setLayout(qt.QFormLayout())
        self.fileFormatGroup = qt.QButtonGroup(self.fileFormatSelectFrame)
        self.nrrdButton = qt.QRadioButton("NRRD")
        self.nrrdButton.checked = True
        self.niftiButton = qt.QRadioButton("NIFTI")
        self.fileFormatGroup.addButton(self.nrrdButton)
        self.fileFormatGroup.addButton(self.niftiButton)
        self.fileFormatSelectFrame.layout().addRow(self.nrrdButton, self.niftiButton)        
        self.settingsCollapsibleButton.layout().addRow(self.fileFormatLabel, self.fileFormatSelectFrame)
        
        # Use input DICOM Patient Directory names as PatientID or infer from DICOM Metadata
        self.patientIDLabel = qt.QLabel("Infer Patient IDs from:  ", self.settingsCollapsibleButton)
        self.patientIDLabel.toolTip = "Use input DICOM Patient Directory names as PatientID or infer from DICOM Metadata"
        
        self.patientIDSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.patientIDSelectFrame.setLayout(qt.QFormLayout())
        self.patientIDGroup = qt.QButtonGroup(self.patientIDSelectFrame)
        self.metadataButton = qt.QRadioButton("Series DICOM Metadata")
        self.metadataButton.checked = True
        self.inputDirButton = qt.QRadioButton("Input Patient Subdirectories")
        self.patientIDGroup.addButton(self.metadataButton)
        self.patientIDGroup.addButton(self.inputDirButton )
        self.patientIDSelectFrame.layout().addRow(self.metadataButton, self.inputDirButton)        
        self.settingsCollapsibleButton.layout().addRow(self.patientIDLabel, self.patientIDSelectFrame)
        
        # Center Images option
        self.centerImagesLabel = qt.QLabel("Center Images:  ", self.settingsCollapsibleButton)
        
        self.centerImagesSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.centerImagesSelectFrame.setLayout(qt.QFormLayout())
        self.centerImagesGroup = qt.QButtonGroup(self.centerImagesSelectFrame)
        self.centerImagesButton = qt.QRadioButton("Yes")
        self.noCenterImagesButton = qt.QRadioButton("No")
        self.noCenterImagesButton.checked = True
        self.centerImagesGroup.addButton(self.centerImagesButton)
        self.centerImagesGroup.addButton(self.noCenterImagesButton)
        self.centerImagesSelectFrame.layout().addRow(self.centerImagesButton, self.noCenterImagesButton)        
        self.settingsCollapsibleButton.layout().addRow(self.centerImagesLabel, self.centerImagesSelectFrame)
        
        # Center Labels option
        self.centerLabelsLabel = qt.QLabel("Center Labels:  ", self.settingsCollapsibleButton)
        
        self.centerLabelsSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.centerLabelsSelectFrame.setLayout(qt.QFormLayout())
        self.centerLabelsGroup = qt.QButtonGroup(self.centerLabelsSelectFrame)
        self.centerLabelsButton = qt.QRadioButton("Yes")
        self.noCenterLabelsButton = qt.QRadioButton("No")
        self.noCenterLabelsButton.checked = True
        self.centerLabelsGroup.addButton(self.centerLabelsButton)
        self.centerLabelsGroup.addButton(self.noCenterLabelsButton)
        self.centerLabelsSelectFrame.layout().addRow(self.centerLabelsButton, self.noCenterLabelsButton)        
        self.settingsCollapsibleButton.layout().addRow(self.centerLabelsLabel, self.centerLabelsSelectFrame)
        
        # Parse and Save DICOM Metadata to CSV
        self.metadataExtractLabel = qt.QLabel("DICOM Metadata Extraction", self.settingsCollapsibleButton)
        self.metadataExtractLabel.toolTip = "Extract and Save all DICOM Metadata to a CSV file"
        
        self.metadataExtractSelectFrame = qt.QFrame(self.settingsCollapsibleButton)
        self.metadataExtractSelectFrame.setLayout(qt.QFormLayout())                
        self.metadataExtractGroup = qt.QButtonGroup(self.metadataExtractSelectFrame)
        self.extractCSVButton = qt.QRadioButton("CSV")
        self.extractCSVButton.checked = True
        #self.extractJSONButton = qt.QRadioButton("JSON")        
        self.doNotExtractButton = qt.QRadioButton("None")
        self.metadataExtractGroup.addButton(self.extractCSVButton)
        self.metadataExtractGroup.addButton(self.doNotExtractButton)
        self.metadataExtractSelectFrame.layout().addRow(self.extractCSVButton, self.doNotExtractButton)       
        self.settingsCollapsibleButton.layout().addRow(self.metadataExtractLabel, self.metadataExtractSelectFrame)
                   
        # Apply Batch Convert button
        self.applyBatchButton = qt.QPushButton("Apply Batch Convert")
        self.applyBatchButton.toolTip = "Batch convert DICOM to NRRD or NIFTI files" 
        self.layout.addWidget(self.applyBatchButton)
        self.applyBatchButton.enabled = False
        
        #---------------------------------------------------------
        # Connections
        self.input1Button.connect('clicked(bool)', self.onInput1Button)
        self.input2Button.connect('clicked(bool)', self.onInput2Button)
        self.selectConvertButton.toggled.connect(self.selectConvert)
        self.addContourButton.connect('clicked(bool)', self.addContourFilterWidget)
        self.applyBatchButton.connect('clicked(bool)', self.onBatchApply) 
        
    def selectConvert(self):
        if self.selectConvertButton.enabled:
            self.contourConvertCollapsibleButton.enabled = True
            self.contourConvertCollapsibleButton.collapsed = False
        else:
            self.contourConvertCollapsibleButton.enabled = False
            self.contourConvertCollapsibleButton.collapsed = True
  
    def onInput1Button(self):
        self.inputPatientDir = qt.QFileDialog.getExistingDirectory()
        self.input1Button.text = self.inputPatientDir
        if self.inputPatientDir and self.outputPatientDir: self.applyBatchButton.enabled = True
    
    def onInput2Button(self):
        self.outputPatientDir = qt.QFileDialog.getExistingDirectory()
        self.input2Button.text = self.outputPatientDir
        if self.inputPatientDir and self.outputPatientDir: self.applyBatchButton.enabled = True
       
    def addContourFilterWidget(self):      
        contourFilter = ContourFilterWidget(parent=self.keywordsScrollWidget)       
        self.keywordsScrollWidget.layout().addRow(contourFilter)
    
    def getContourFilters(self):      
        contourFilterWidgets = [childWidget for childWidget in self.keywordsScrollWidget.children() if childWidget.className()=="ContourFilterWidget"]
        if len(contourFilterWidgets) == 0: return None

        contourFilters = [filterWidget.getContourFilterDict() for filterWidget in contourFilterWidgets]
        return contourFilters
        
    def onBatchApply(self):
        self.applyBatchButton.enabled = False
        
        if self.nrrdButton.checked: self.converterSettings["fileformat"] = ".nrrd"
        elif self.niftiButton.checked: self.converterSettings["fileformat"] = ".nii"
        
        if self.metadataButton.checked: self.converterSettings["inferpatientid"] = "metadata"
        elif self.inputDirButton.checked: self.converterSettings["inferpatientid"] = "inputdir"
        
        if self.noConvertButton.checked:
            self.converterSettings['convertcontours'] = 'None'
            self.contourFilters = []
        elif self.allConvertButton.checked:
            self.converterSettings['convertcontours'] = 'All'
            self.contourFilters = []
        elif self.selectConvertButton.checked:
            self.converterSettings['convertcontours'] = 'Select'
            self.contourFilters = self.getContourFilters()
        
        if self.noCenterImagesButton.checked: 
            self.converterSettings["centerimages"] = False
        else:    
            self.converterSettings["centerimages"] = True
            
        if self.noCenterLabelsButton.checked:    
            self.converterSettings["centerlabels"] = False
        else:
            self.converterSettings["centerlabels"] = True        
            
        #batchConverterTools.BatchConvertDICOMtoNRRD.batchConvert(self.inputPatientDir, self.outputPatientDir, self.contourFilters, self.converterSettings)
        batchConverterLogic = batchConverterTools.BatchConvertDICOMtoNRRD.BatchConverterLogic(self.inputPatientDir, self.outputPatientDir, self.contourFilters, self.converterSettings)
        batchConverterLogic.batchConvert()
        
        if self.extractCSVButton.checked:
            DicomHeaderParserInstance = batchConverterTools.MetadataExtractor.DicomHeaderParser(self.inputPatientDir)
            DicomHeaderParserInstance.ExecuteDicomHeaderParser()
            DicomHeaderParserInstance.WriteToCSVFile(outputDir=self.outputPatientDir)        
            
        self.applyBatchButton.enabled = True
        self.applyBatchButton.text = "Apply Batch Convert"
    
class ContourFilterWidget(qt.QWidget):
    def __init__(self, parent=None):
        super(ContourFilterWidget, self).__init__(parent)
        
        self.inputKeywords = qt.QLineEdit("")
        self.inputKeywords.setPlaceholderText("Search Keywords")
        self.excludeKeywords = qt.QLineEdit("")
        self.excludeKeywords.setPlaceholderText("Exclusion Keywords")
        self.deleteButton = qt.QPushButton("Delete")
        self.deleteButton.connect('clicked()', self.delete) 
        
        layout = qt.QHBoxLayout()
        layout.addWidget(self.inputKeywords)
        layout.addWidget(self.excludeKeywords)
        layout.addWidget(self.deleteButton)
        self.setLayout(layout)
        
    def getContourFilterDict(self):  
        if self.inputKeywords.text == '': inputContourKeywords = []   
        else: inputContourKeywords = [str(keyword.strip()) for keyword in self.inputKeywords.text.split(',')]
        
        if self.excludeKeywords.text == '': excludeContourKeywords = []       
        else: excludeContourKeywords = [str(keyword.strip()) for keyword in self.excludeKeywords.text.split(',')]        
        
        contourFilter = {"Include": inputContourKeywords, "Exclude": excludeContourKeywords}
        
        return contourFilter
        

        
        
            