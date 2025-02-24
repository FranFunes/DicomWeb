from queue import Queue
from typing import List, Union, Callable
import logging, os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pydicom.uid import UID
from pydicom.dataset import Dataset

from pynetdicom import AE, evt, StoragePresentationContexts, build_role, build_context, debug_logger
from pynetdicom.association import Association
from pynetdicom.events import Event
from pynetdicom.sop_class import (
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    StudyRootQueryRetrieveInformationModelGet,
    Verification
)

# Setup logging behaviour
app_logger = logging.getLogger('__main__')

def default_query(level: str):

    """
        Sets default parameters for study or series level queries.

        Args:
            · level: 'SERIES' or 'STUDY' with the level of the query.           
            

        Returns: a pydicom.Dataset with the default parameters for the query

    """
    
    ds = Dataset()

    # Set default parameters for the study-level query
    if level == 'STUDY':        
        ds.PatientName = ''
        ds.PatientID = ''
        ds.StudyDescription = ''
        ds.StudyDate = ''
        ds.ModalitiesInStudy = ''
        ds.NumberOfStudyRelatedSeries = ''
    
    # Set default parameters for the series-level query
    elif level == 'SERIES':
        ds.SeriesDescription= ''
        ds.SeriesNumber = ''
        ds.Modality = ''
        ds.NumberOfSeriesRelatedInstances = ''
        ds.ImagesInAcquisition = ''        

    else:
        app_logger.error('Level must be either "SERIES" or "STUDY"')
        raise ValueError('Level must be either "SERIES" or "STUDY"')

    return ds

def default_store_handler(event: Event, 
        write_to_disk: str = True, root_dir: str = 'incoming', 
        dcm_path: List[str] = ['PatientName', 'StudyDescription', 'SeriesDescription'], 
        dcm_filename: str = 'SOPInstanceUID',        
        output_queue: Queue = None, keep_fields: List[Union[str, int]] = None) -> int:

    """
    
    Default store handler for the Store SCP. It has two possible modes:
        · Write the dataset to disk: active when "write_to_disk" is True. In this case, each dataset received
        is written to a file named as selected by the "dcm_filename" argument, and in a path structure build
        according to the "dcm_path" argument. "dcm_path" must be a list of str representing DICOM field names.
        · Put the dataset in a Queue.queue object, so that it can be accesed later using queue.get(). This mode
        will be active if a Queue.queue is passed as output_queue argument. Note that the dataset will be held
        in memory in this case, until another process consumes it. Optionally, a subset of dicom fields (instead
        of the whole dataset) can be kept. This is selected with the keep_fields argument.

    Arguments:
        · write_to_disk (bool, default: True): selects if received datasets are written to disk
        · root_dir (str, default: incoming): the root for the path of dicom files written to disk
        · dcm_path (list of str): selects which dicom fields are used to form the path to each dicom file
        written to disk (defaults to PatientName, StudyDescription and SeriesDescription)
        · dcm_filename: the dicom field that will be used as the filename for each dicom file written to disk
        (defaults to SOPInstanceUID; InstanceNumber can also be used but its not guaranteed to be unique)
        · output_queue (Queue.queue object, default: None): if not None, received datasets are put in the
        Queue.queue object (and can be accesed later using the .get method on that object). Only the dicom 
        fields selected in "keep_fields" will be kept.
        · keep_fields: a list of str or int to select the dicom fields that should be kept when putting the
        datasets on output_queue. Strings must be standard dicom field names; ints must be in the form 0xggggffff,
        where g and f are the numbers for the corresponding dicom tag. If

    """
    
    try:
        ds = event.dataset
        ds.file_meta = event.file_meta
        if write_to_disk:            
            filedir = os.path.join(root_dir, *[str(ds[field].value).replace('/','_') for field in dcm_path])
            os.makedirs(filedir, exist_ok = True)
            filepath = os.path.join(filedir, str(ds[dcm_filename].value).replace('/','_'))
            ds.save_as(filepath, write_like_original = False)
    except:
        app_logger.error("SCP: dataset could not be written to disk")

    if output_queue:
        try:
            output_ds = Dataset()
            if not keep_fields:
                output_ds = ds
            else:
                for key in keep_fields:
                    if key in ds:
                        output_ds[key] =  ds[key]
                    else:
                        setattr(output_ds, key, '')
                if write_to_disk:            
                    output_ds.filepath = filepath
            output_queue.put(output_ds)

        except Exception as e:
            app_logger.error("dataset could not put in output queue")
    
    return 0x0000 

class DicomInterface(AE):    

    """ 
        
    
    """

    def __init__(self, address = '0.0.0.0', port = None, acse_timeout:int = 60,
                       store_handler: Callable = default_store_handler, *args, **kwargs):

        """
        
        Args:
            · ae_title: str, optional, default 'PYNETDICOM'
            · address: str, optional, default '0.0.0.0'
                The ip address of the Store SCP
            · port: int, optional, default None
                The port to use for the Store SCP. Can be ommited during instantiation, but 
                must be set to a valid int before using starting store SCP.
            · store_handler: an appropiate handler for a C-STORE request (see pynetdicom documentation for
            more hints on how to write an appropiate handler). If not specified, the default handler defined
            above will be used.
        
        """
        # Get ae_title to initalize class
        super().__init__(*args,**kwargs)

        # Set class properties
        self.address = address
        self.port = port
        self.store_handler = store_handler
        self.store_scp_active = False
        self.acse_timeout = 120
        self.dimse_timeout = 120
        self.network_timeout = 120

        # AE configuration
        # Requested contexts (when acting as Store SCU)
        self.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
        self.add_requested_context(StudyRootQueryRetrieveInformationModelGet)  
        self.add_requested_context(Verification)

                
        # Add supported contexts (when acting as SCP)
        self.supported_contexts = StoragePresentationContexts
        self.add_supported_context(Verification)
        self.add_supported_context('1.2.840.113619.4.30') # GE PET Raw data


    def start_store_scp(self) -> None:        

        """         

            Starts the store SCP listener in server (i.e. non blocking) mode.

        """                      
        if not self.port:
            app_logger.error("Listening port must be specified before starting the StoreSCP. Set it to a int in the port attribute.")
            raise(ValueError('Listening port must be specified before starting the StoreSCP. Set it to a int in the port attribute.'))
        
        # Implement a handler for evt.EVT_C_ECHO
        def handle_echo(event):
            """Handle a C-ECHO request event."""
            return 0x0000

        handlers = [(evt.EVT_C_STORE, self.store_handler), (evt.EVT_C_ECHO, handle_echo)]            

        # Start listening for incoming association requests
        self.server = self.start_server((self.address, self.port), evt_handlers=handlers, block = False)
        self.store_scp_active = True
        # Show message       
        app_logger.info('Starting store SCP listener ' + self.ae_title.strip() + '@' + self.address + ':' + str(self.port))

    def stop_store_scp(self) -> None:
        
        """ Stops the SCP """
        if hasattr(self,'server'):
            self.server.shutdown()
        self.store_scp_active = False
        app_logger.debug("Store SCP stopped")

    def get_association(self, device: dict, *args,**kwargs) -> Association:

        """

        If a live association with the device exists, return it. If not, start it and return it.

        device: a dict with the following keys/values:
            · ae_title: str with the ae_title of the remote application
            · address: str with the ip address of the remote application
            · port: int with the TCP port where the remote application is running          
        
        Returns: an active association with the selected device

        Raises:
            RuntimeError if association could not be established.
        """

        # Keep neccesary keys only
        device = {'ae_title': device['ae_title'],
                  'address': device['address'],
                  'port': device['port']}
        
        for assoc in self.active_associations:
            remote = {key: assoc.remote[key] for key in device.keys()}
            if remote == device:
                return assoc
        
        assoc = self.associate(device['address'], device['port'], ae_title = device['ae_title'], *args, **kwargs)

        if not assoc.is_established:
            raise(RuntimeError(f"Association with {device['ae_title']}@{device['address']}:{device['port']} could not be established"))

        return assoc
            
    def release_connections(self) -> None:
        """
            Release all active associations
        """        

        for assoc in self.active_associations:
            assoc.release()

    def echo(self, device: dict) -> int:

        """
            device: dict with address, port and ae_title

        """
        try:
            assoc = self.get_association(device)

            if assoc.is_established:
                echo_response = assoc.send_c_echo()
                if 'Status' in echo_response: 
                    return echo_response.Status
            else:
                return -1
        except RuntimeError:
            app_logger.debug(f"DicomInterface - echo: Association with {device['ae_title']}@{device['address']}:{device['port']} could not be established")
            return -1

    def query_device(self, device: dict, search_criteria: Union[dict, Dataset]) ->  List[Dataset]:

        """        
            Query a device with custom search_criteria

        """

        # Get the association with the device
        try:
            assoc = self.get_association(device)
        except RuntimeError:
            app_logger.debug(f"DicomInterface - query_device: Association with {device['ae_title']}@{device['address']}:{device['port']} could not be established")
            return []

        # Set query parameters
        ds = Dataset()
        ds.update(search_criteria)
        
        # Start the query
        app_logger.debug(f"DicomInterface - query_device: Querying association with {assoc.acceptor.ae_title}")
        try:
            c_find_resp = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)    
            # Extract results
            query_results = list(c_find_resp)  
        except RuntimeError:      
            app_logger.debug(f"DicomInterface - query_device: Association with {device['ae_title']}@{device['address']}:{device['port']} is not stablished")
            query_results = []

        # Format the output
        responses = []
        for element in query_results:
            # Discard None
            if element[1]:
                responses.append(element[1])

        app_logger.debug(f"DicomInterface - query_device: Got {len(responses)} results from query to {assoc.acceptor.ae_title}")

        return responses

    def query_studies_in_device(self, device: dict, 
        search_criteria: Union[dict, Dataset] = None, 
        responses: Union[dict, Dataset] = None) ->  List[Dataset]:

        """
        
            A shortcut to query studies in a device (not need to set QueryRetrieveLevel).
            The parameters for the search can be selected using the "search_criteria" argument, which should
            be a pydicom.dataset or a dict with study-level fields and values for the query.
            The information to be included in the responses can be selected using the "responses", that should
            be a dict or pydicom.dataset object with the keys to fetch and blank values. If not specified,
            a set of default fields are requested.

            Example:
                search_criteria = {'StudyDate':'20230201', 'ModalitiesInStudy':'PT'}
                responses = {'PatientName':'', 'StudyDescription':''}
                Searches for PET studies on 1/2/2023 and asks the remote device to report patient name and
                study description for each result.

        """

        # Set query parameters
        ds = Dataset()        
        if search_criteria:
            ds.update(search_criteria)
        if not responses:
            responses = default_query('STUDY')        
        new_entries = {key:value for key,value in responses.items() if not key in ds}
        ds.update(new_entries)           
        ds.QueryRetrieveLevel = 'STUDY'
        ds.StudyInstanceUID = ''

        return self.query_device(device, ds)

    def query_series_in_study(self, device: dict, StudyInstanceUID: Union[str, UID],
        search_criteria : Union[Dataset, dict] = None,
        responses : Union[Dataset, dict] = None) -> List[Dataset]:

        """
        
            A shortcut to query series in a study.
            The parameters for the search can be selected using the "search_criteria" argument, which should
            be a pydicom.dataset or a dict with series-level fields and values for the query.
            StudyInstanceUID must always be specified, so it has a dedicated argument and does not need to
            be included in search_criteria.

            The information to be included in the responses can be selected using the "responses", that should
            be a dict or pydicom.dataset object with the keys to fetch and blank values. If not specified,
            a set of default fields are requested.
            

            Example:
                search_criteria = {'Modality':'PT'}
                responses = {'SeriesDescription':'', 'SeriesTime':''}
                Searches for PET series on the selected study and asks the remote device to report the
                series description and series time for each result.

        """

        # Set query parameters
        ds = Dataset()        
        if search_criteria:
            ds.update(search_criteria)
        if not responses:
            responses = default_query('SERIES')        
        new_entries = {key:value for key,value in responses.items() if not key in ds}
        ds.update(new_entries)

        ds.QueryRetrieveLevel = 'SERIES'
        ds.StudyInstanceUID = StudyInstanceUID
        ds.SeriesInstanceUID = ''

        return self.query_device(device, ds)

    def query_imgs_in_series(self, device: dict, StudyInstanceUID: Union[str, UID], SeriesInstanceUID: Union[str, UID],
        search_criteria : Union[Dataset, dict] = None,
        responses : Union[Dataset, dict] = {}) -> List[Dataset]:

        """
        
            A shortcut to query imgs in a series.
            The parameters for the search can be selected using the "search_criteria" argument, which should
            be a pydicom.dataset or a dict with image-level fields and values for the query.
            StudyInstanceUID and SeriesInstanceUID must always be specified, so it has a dedicated argument and does not need to
            be included in search_criteria.

            The information to be included in the responses can be selected using the "responses", that should
            be a dict or pydicom.dataset object with the keys to fetch and blank values. If not specified,
            the SOPInstanceUID is the only field guaranteed to be retrieved.
            

        """

        # Create a dataset for the query
        ds = Dataset()
        if search_criteria:
            ds.update(search_criteria)
             
        new_entries = {key:value for key,value in responses.items() if not key in ds}
        ds.update(new_entries)
        ds.QueryRetrieveLevel = 'IMAGE'
        ds.StudyInstanceUID = StudyInstanceUID
        ds.SeriesInstanceUID = SeriesInstanceUID
        ds.SOPInstanceUID = ''     
        ds.SOPClassUID = ''   

        return self.query_device(device, ds)

    def query_imgs_in_study(self, device: dict, StudyInstanceUID: Union[str, UID],
        series_search_criteria : Union[Dataset, dict] = None,
        imgs_search_criteria : Union[Dataset, dict] = None,
        responses : Union[Dataset, dict] = {}) -> List[Dataset]:

        """
        
            A shortcut to query all the imgs in a study.
            The parameters for the search can be selected using the "search_criteria" arguments, which should
            be a pydicom.dataset or a dict with series-level and image-level fields and values for the query, respectively.
            StudyInstanceUID and SeriesInstanceUID must always be specified, so it has a dedicated argument and does not need to
            be included in search_criteria.

            The information to be included in the responses can be selected using the "responses", that should
            be a dict or pydicom.dataset object with the keys to fetch and blank values. If not specified,
            the SOPInstanceUID is the only field guaranteed to be retrieved.            

        """

        # Find the series in the study
        series = self.query_series_in_study(device, StudyInstanceUID, series_search_criteria)        
        imgs = []
        for ss in series:
            imgs.extend(self.query_imgs_in_series(device, StudyInstanceUID, ss.SeriesInstanceUID, imgs_search_criteria, responses))

        return imgs

        
    def move_datasets(self, src_device: dict, dst_device_aet: str, datasets: List[Dataset]) -> List[dict]:

        """

            Sends a C-MOVE requests to a remote (source) device or application, to move a list of pydicom.Dataset from
            the source device to a destination device

            Args:
                · datasets: a list of pydicom.Dataset. Each element may represent a Study, Series or Image (this is 
                inferred from the Query/Retrieve Level field), and will be used to start a C-MOVE request.
                · src_device: a dict with the following fields:
                    - ae_title: the source ae_title (str)
                    - address: ip address of the source AE (str)
                    - port: port of the source AE (int)
                · dst_device_aet: the destination ae_title (str)


            Returns: a list with equal size as datasets. Each element is a dictionary, with the number of 
            succesfully sent, warnings and failed operations.

            Note: 
                This function does not check if each element in dataset is appropiate for sending a C-MOVE request. This check is
                up to the user. An appropiate dataset for a C-MOVE request must have:
                · A QueryRetrieveLevel equal to "STUDY", "SERIES", or "IMAGE"
                · Explicit values for all the UIDs in the hierarchy level of the query and upper levels
                (e.g. if "SERIES" QueryRetrieveLevel is used, the dataset must have an StudyInstanceUID and a SeriesInstanceUID)

        """
        
        results = []        
            
        # For each element in datasets, send a C-MOVE request
        try:
            association = self.get_association(src_device)   
            
            for dataset in datasets:                
                
                    ds = Dataset()
                    
                    # Keep relevant fields only            
                    for elem in dataset:
                        if elem.keyword == 'QueryRetrieveLevel':
                            setattr(ds, 'QueryRetrieveLevel', elem.value)
                        if isinstance(elem.value, UID):
                            setattr(ds, elem.keyword, elem.value)                
                    try:
                        c_move_response = association.send_c_move(ds, move_aet = dst_device_aet, query_model = StudyRootQueryRetrieveInformationModelMove)

                        responses = list(c_move_response)
                        
                        # Select the last response with sub-operations data            
                        idx = -1
                        while not -idx > len(responses) and not 'NumberOfCompletedSuboperations' in responses[idx][0]:
                            idx-=1                
                        if -idx > len(responses):
                            results.append({'Completed': None, 'Failed': None, 'Warning': None})
                        else:
                            results.append({'Completed': responses[idx][0]['NumberOfCompletedSuboperations'].value,
                                            'Failed': responses[idx][0]['NumberOfFailedSuboperations'].value,
                                            'Warning': responses[idx][0]['NumberOfWarningSuboperations'].value})                
                    except RuntimeError:
                        results.append({'Completed': None, 'Failed': None, 'Warning': None})
                        app_logger.debug(f"DicomInterface - move_datasets: Association with {src_device['ae_title']}@{src_device['address']}:{src_device['port']} is not stablished")
        
        except RuntimeError:
            app_logger.debug(f"DicomInterface - move_datasets: Association with {src_device['ae_title']}@{src_device['address']}:{src_device['port']} is not stablished")

        return results
            
    def retrieve_datasets(self, src_device: dict, datasets: List[Dataset]) -> List[dict]:
        
        """
        
            A shortcut to make a C-MOVE from the selected device to the local device. Note that,
            for this to work, two conditions must be fullfiled:
                · The local ae_title, ip and port must have been correctly declared
                in the remote (source) device.
                · The local Store SCP must have been succesfuly started with the start_store_scp method.
            See move_datasets method for more details on the arguments.

        """
        if not self.store_scp_active:
            raise RuntimeError('DicomInterface - retrieve_datasets: store scp must be active before using retrieve dataset. Start it with start_store_scp method')

        return self.move_datasets(src_device, self.ae_title, datasets)

    def get_datasets(self, device: dict, datasets: List[Dataset], store_handler: Callable = None) -> List[dict]:
        
        """

            Sends a C-GET request to a remote (source) device or application, to get a list of pydicom.Dataset.
            
            Args:
                · datasets: a list of pydicom.Dataset. Each element may represent a Study, Series or Image (this is 
                inferred from the Query/Retrieve Level field), and will be used to start a C-GET request.
                · src_device: a dict with the following fields:
                    - ae_title: the source ae_title (str)
                    - address: ip address of the source AE (str)
                    - port: port of the source AE (int)
                · store_handler: an appropiate handler for a C-STORE request (see pynetdicom documentation for
                more hints on how to write an appropiate handler). If not specified, the default handler defined
                for the class will be used

            Returns: a list with equal size as datasets. Each element is a dictionary, with the number of 
            succesfully sent, warnings and failed operations.

            Note: 
                This function does not check if each element in dataset is appropiate for sending a C-GET request. This check is
                up to the user. An appropiate dataset for a C-GET request must have:
                · A QueryRetrieveLevel equal to "STUDY", "SERIES", or "IMAGE"
                · Explicit values for all the UIDs in the hierarchy level of the query and upper levels
                (e.g. if "SERIES" QueryRetrieveLevel is used, the dataset must have an StudyInstanceUID and a SeriesInstanceUID)

        """
        # Set default store handler
        if not store_handler:
            store_handler = self.store_handler

        # Set the presentation contexts for the C-GET association
        contexts = [build_context(StudyRootQueryRetrieveInformationModelGet)]

        # Add the SOP class uids present in the datasets to the requested contexts for the association        
        new_uids = set([ds.SOPClassUID for ds in datasets])
        for uid in new_uids:
            contexts.append(build_context(uid))

        # Stablish a specific association with role negotiation for the c_get
        roles = []
        for context in contexts[1:]:
            roles.append(build_role(context.abstract_syntax, scp_role=True))        
        handlers = [(evt.EVT_C_STORE, store_handler)]
        association = self.associate(device['address'], device['port'], contexts, device['ae_title'], ext_neg = roles, evt_handlers = handlers)
        results = []        
            
        # For each element in datasets, send a C-GET request
        if association.is_established:                 
            for dataset in datasets:              
                
                    ds = Dataset()                    
                    # Keep relevant fields only            
                    for elem in dataset:
                        if elem.keyword == 'QueryRetrieveLevel':
                            setattr(ds, 'QueryRetrieveLevel', elem.value)
                        if isinstance(elem.value, UID):
                            setattr(ds, elem.keyword, elem.value)
                    try:
                        c_get_response = association.send_c_get(ds, query_model = StudyRootQueryRetrieveInformationModelGet)
                        responses = list(c_get_response)
                        
                        # Select the last response with sub-operations data            
                        idx = -1
                        while not -idx > len(responses) and not 'NumberOfCompletedSuboperations' in responses[idx][0]:
                            idx-=1                
                        if -idx > len(responses):
                            results.append({'Completed': None, 'Failed': None, 'Warning': None})
                        else:
                            results.append({'Completed': responses[idx][0]['NumberOfCompletedSuboperations'].value,
                                            'Failed': responses[idx][0]['NumberOfFailedSuboperations'].value,
                                            'Warning': responses[idx][0]['NumberOfWarningSuboperations'].value})     
                    except RuntimeError:
                        app_logger.debug(f"DicomInterface - get_datasets: Association with {device['ae_title']}@{device['address']}:{device['port']} is not stablished")
                        results.append({'Completed': None, 'Failed': None, 'Warning': None})
                        
        return results

    def store_datasets(self, device: dict, datasets: List[Union[Dataset, str, Path]]) -> List[dict]:
        
        """

            Sends a C-STORE request to a remote (destination) device or application, to store a list of pydicom.Dataset.
            
            Args:
                · datasets: a list of pydicom.dataset.Dataset, str or pathlib.Path
                    The list of DICOM datasets to send to the peer or the file path to the
                    datasets to be sent. If a file path then the datasets will be read
                    and decoded using :func:`~pydicom.filereader.dcmread`.
                · device: a dict with the following fields for the destination:
                    - ae_title: the source ae_title (str)
                    - address: ip address of the source AE (str)
                    - port: port of the source AE (int)

            Returns: a list with equal size as datasets. Each element is a dictionary, with the number of 
            succesfully sent, warnings and failed operations.

        """

        # Add the SOP class uids present in the datasets to the requested contexts for the association
        contexts = []
        new_uids = set([ds.SOPClassUID for ds in datasets])
        for uid in new_uids:
            contexts.append(build_context(uid))

        # Create association
        association = self.associate(device['address'], device['port'], contexts, device['ae_title'])     
        
        # Send the C-STORE
        results = []      
        
        for dataset in datasets:
            try:
                status = association.send_c_store(dataset)
                if status and status.Status == 0:
                    results.append(True)
                else:
                    results.append(False)
            except RuntimeError:
                results.append(False)
                app_logger.debug(f"DicomInterface - store_datasets: Association with {device['ae_title']}@{device['address']}:{device['port']} is not stablished")
                
        return results

    def get_studies(self, device: dict, search_criteria: Union[dict, Dataset] = None,
        store_handler: Callable = None):

        """

        Sends a study level query/retrieve to a remote device, using C-GET to get the results.
        Process the incoming datasets using store_handler.
        See the following methods for more details on the arguments
            · query_studies_in_device
            · get_datasets    

        """
        datasets = self.query_studies_in_device(device, search_criteria, {'StudyInstanceUID':''})

        return self.get_datasets(device, datasets, store_handler)

    def retrieve_studies(self, device: dict, search_criteria: Union[dict, Dataset] = None):

        """

        Sends a study level query/retrieve to a remote device, using C-MOVE to get the results.
        Process the incoming datasets using store_handler.
        See the following methods for more details on the arguments
            · query_studies_in_device
            · retrieve_datasets
            · move_datasets

        """
        datasets = self.query_studies_in_device(device, search_criteria, {'StudyInstanceUID':''})

        return self.retrieve_datasets(device, datasets)

    def get_series_in_study(self, device: dict, StudyInstanceUID: Union[str, UID],
        search_criteria: Union[dict, Dataset] = None,
        store_handler: Callable = None):

        """

        Sends a series level query/retrieve to a remote device, using C-GET to get the results.
        Process the incoming datasets using store_handler.
        See the following methods for more details on the arguments
            · query_series_in_device
            · get_datasets    

        """
        datasets = self.query_series_in_study(device, StudyInstanceUID, search_criteria, {'SeriesInstanceUID':''})
        
        return self.get_datasets(device, datasets, store_handler)
        
    def retrieve_series(self, device: dict, StudyInstanceUID: Union[str, UID],
        search_criteria: Union[dict, Dataset] = None):

        """

        Sends a series level query/retrieve to a remote device, using C-MOVE to get the results.
        See the following methods for more details on the arguments
            · query_series_in_device
            · move_datasets    

        """
        datasets = self.query_series_in_study(device, StudyInstanceUID, search_criteria, {'SeriesInstanceUID':''})

        return self.retrieve_datasets(device, datasets)