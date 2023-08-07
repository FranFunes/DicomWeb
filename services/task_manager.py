from time import sleep
from datetime import datetime
from queue import Queue
import threading, logging

import pandas as pd
from numpy import argmax
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelMove
from pydicom.dataset import Dataset

from app_pkg import application
from app_pkg.db_models import Device
from services.dicom_interface import DicomInterface

logger = logging.getLogger('__main__')

class DeviceTasksHandler():
    """
    
    A class to manage the tasks associated with one device. The class works mainly with the components:
    · A dictionary of tasks (self.tasks_list), with task_ids as keys, and dictionary as values containing the following keys:
        - priority: the priority for this task
        - status: the task status (can be 'active','paused','failed','completed')
        - progress: the completion state in percentage
        - data: the data associated with this task (type of task to perform, source and destination devices, 
        identifiers for study/series to move/get, patient and study info, etc).
        - step: a handler to perform one step of this task (like an iterator).
    · A queue.Queue object where modifications to the tasks list are put to be processed. Each element put in the 
    queue is a dictionary, with the following keys:
        - action: the modification to perform. Must be one of 'new','pause','continue','retry','rush',
        'delete','complete','fail'.
        - task_id: the task_id of the task to modify
        - data: only needed in case action is new; the data to put in the tasks_list

    The tasks are performed sequentially in a thread for this class. There is only one thread for the whole class. If multiple
    processing threads are needed, multiple instances of this class should be used.
    In each step, the main process reads the task_modifiers queue. If there are any modifications to perform, those are performed
    and the loop starts again. If there are not, the following task to be performed is defined and one step of that task is performed.
    After checking for tasks completion or failure, and generating the corresponding modifier in those cases, the loop starts again.

    The processing can be stopped by setting an stop event in the class, or by putting the 'stop_thread' action in the queue.
    
    """

    def __init__(self):

        self.tasks_list = {}
        self.task_modifiers = Queue()

        # Initialize DICOM interface
        with application.app_context():
            self.ae = DicomInterface(ae_title = Device.query.get('__local_store_SCP__').ae_title)
        
        # Initialize the current task id to None
        self.current_task_id = None
        
        self.start()

    def start(self):

        # Set an event to stop the thread later 
        self.stop_event = threading.Event()

        # Create and start the thread
        self.main_thread = threading.Thread(target = self._main, args = ())        
        self.main_thread.start()        

    def stop(self):

        """
        
            Stops the thread by setting an Event.

        """

        self.stop_event.set()
        self.main_thread.join()

    def manage_task(self, id, action, data = None) -> None:
        modifier = {'action':action, 'task_id':id, 'data':data}
       
        logger.debug(f"manage_task - new modifier: action: {action}, task_id: {id}")
        self.task_modifiers.put(modifier)

    def _main(self):

        while not self.stop_event.is_set() or not self.task_modifiers.empty() or self._tasks_pending():
            
            if not self.task_modifiers.empty():                
                # Execute task modifier                
                modifier = self.task_modifiers.get()
                logger.debug(f"_main: new modifier with action: {modifier['action']}, task_id: {modifier['task_id']}")
                self._modify_task(modifier)
                # Set the next task to be performed
                self._next_task()
            elif not self.current_task_id == None:
                # Perform a step for the current task    
                logger.debug(f"_main - step, current task: {self.current_task_id}")
                self._task_step(self.current_task_id)
            else:
                sleep(1)            
            

    def _tasks_pending(self):

        return 'active' in [task['status'] for task in self.tasks_list.values()]
    
    def _modify_task(self, modifier):

        action = modifier['action']
        id = modifier['task_id']
        
        if action == 'new':
            self._new_task(id, modifier['data'])
            logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")
        elif action == 'pause':
            if self.tasks_list[id]['status'] in ['active','pending']:
                logger.debug(f"_modify_task - Paused task with id {id}")
                self.tasks_list[id]['status'] = 'paused'
                logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")
                
        elif action == 'continue':
            if self.tasks_list[id]['status'] == 'paused':
                logger.debug(f"_modify_task - Continue task with id {id}")
                self.tasks_list[id]['status'] = 'pending'                
                
        elif action == 'retry':
            # Get known task data
            logger.debug(f"_modify_task - Retry task with id {id}")
            task_data = self.tasks_list[id]['data']
            self.tasks_list.pop(id)  
            self._new_task(id, task_data)            
            logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")
            
        elif action == 'rush':
            if not self.tasks_list[id]['status'] in ['completed','failed']:
                logger.debug(f"_modify_task - Rush task with id {id}")
                current_priorities = [task['priority'] for task in self.tasks_list.values()]
                self.tasks_list[id]['priority'] = max(current_priorities) + 1                
                logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")

        elif action == 'delete':
            if 'association' in self.tasks_list[id]:
                self.tasks_list[id]['association'].release()
            self.tasks_list.pop(id)
            logger.debug(f"_modify_task - Delete task with id {id}")
            logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")

        elif action == 'complete':
            logger.debug(f"_modify_task - Completed task with id {id}")            
            self.tasks_list[id]['status'] = 'completed'
            logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")

        elif action == 'fail':
            logger.debug(f"_modify_task - Failed task with id {id}")
            self.tasks_list[id]['status'] = 'failed'
            logger.debug(f"_modify_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")
    
    def _next_task(self):
        
        # Find the active task with the highest priority
        active_tasks = [(id, task) for id, task in self.tasks_list.items() if task['status'] in ['active','pending']]
        
        if not active_tasks:
            self.current_task_id = None
            logger.debug(f"_next_task - No active/pending tasks")
        else:            
            next_task_idx = argmax([task['priority'] for id, task in active_tasks])
            next_task_id = active_tasks[next_task_idx][0]
            logger.debug(f"_next_task - Previous task id: {self.current_task_id}")
            logger.debug(f"_next_task - Next task id: {next_task_id}")
            # Change active and pending status if current task id is different from new one
            if next_task_id != self.current_task_id:
                if (not self.current_task_id == None) and self.tasks_list[self.current_task_id]['status'] == 'active':
                    logger.debug(f"_next_task - Changing task {self.current_task_id} to pending")
                    self.tasks_list[self.current_task_id]['status'] = 'pending'                
                logger.debug(f"_next_task - Changing task {next_task_id} to active")
                self.tasks_list[next_task_id]['status'] = 'active'           
                logger.debug(f"_next_task - Tasks status: {[(id, task['status'], task['priority']) for id,task in self.tasks_list.items()]}")            
                self.current_task_id = next_task_id        

    def _task_step(self, task_id):

        logger.debug(f"_task_step - task_id: {task_id}")
        current_task = self.tasks_list[task_id]
        # Take the step
        try:
            # Update task progress   
            progress = next(current_task['step'])    
            logger.debug(f"_task_step - step success, progress: {progress}")
            current_task['progress'] = progress
        except ValueError as e:
            # Set task as completed
            self.tasks_list[task_id]['association'].release()
            logger.debug(f"_task_step - value error")
            logger.debug(repr(e))
            self.manage_task(task_id, action = 'complete')
        except StopIteration as e:
            self.tasks_list[task_id]['association'].release()
            logger.debug(f"_task_step - stop iteration")
            self.manage_task(task_id, action = 'complete')        
        except RuntimeError as e:
            # Set task as failed
            self.tasks_list[task_id]['association'].release()
            logger.debug(f"_task_step - runtime error")
            logger.debug(repr(e))
            self.manage_task(task_id, action = 'fail')
    
    def _new_task(self, id, data):

        # Set the lowest priority
        current_priorities = [task['priority'] for task in self.tasks_list.values()]
        try:            
            priority = min(current_priorities) - 1
        except ValueError:
            priority = 1
        
        # Create a handler (an iterator) to take one step on this task
        task_step_iterator = self._create_task_step_handler(id, data)
        task = {
            'data': data,
            'status': 'pending',
            'priority': priority,
            'step': task_step_iterator,
            'progress': '-'
        }
        
        # Append the task to the tasks list
        self.tasks_list[id] = task

        logger.debug(f"_new_task -  Added new task with id {id} and priority {priority}")

    def _create_task_step_handler(self, task_id, task_data):

        if task_data['type'] == 'MOVE':
            
            # Get source from database      
            s = task_data['source']
            if s == 'local':
                s = '__local_store_SCP__'
            with application.app_context():
                try:
                    device = Device.query.get(s)
                    assert device
                except AssertionError:
                    logger.error(f"Device {s} not found")
                    
            destination = task_data['destination']

            # Get the number of imgs to move
            imgs = task_data['ImgsStudy'] if task_data['level'] == 'STUDY' else task_data['ImgsSeries']

            # Create a new DICOM association to perform the C-MOVE
            source = {attr:getattr(device, attr) for attr in ["ae_title","port","address"]}
            association = self.ae.get_association(source)
            self.tasks_list[task_id]['association'] = association

            # Create the dataset for the C-MOVE operation
            ds = Dataset()
            ds.QueryRetrieveLevel = task_data['level']
            ds.StudyInstanceUID = task_data['StudyInstanceUID']
            if task_data['level'] == 'SERIES': ds.SeriesInstanceUID = task_data['SeriesInstanceUID']

            c_move_responses = association.send_c_move(ds, move_aet = destination, query_model = StudyRootQueryRetrieveInformationModelMove)

            while True:
                try:
                    rsp = next(c_move_responses)
                except StopIteration:
                    # I raise ValueError because exception is taken as RuntimeError insted of StopIteration when I raise StopIteration                                                            
                    raise ValueError                    
                if not bool(rsp[0]):
                    # An empty response indicates a failure state. Raise RuntimeError
                    raise RuntimeError                
                try:
                    completed = rsp[0]['NumberOfCompletedSuboperations'].value
                except:
                    completed = 0                
                progress = f"{completed} / {imgs}"
                yield progress            
        
        elif task_data['type'] == 'GET':

            # Not implemented yet. Use a 'dummy' progress instead
            for i in range(100):
                progress = f"{i}/100"
                yield progress

class TaskManager():

    def __init__(self):

        # Read previous session data, or initialize data
        try:
            data = pd.read_csv('config/pending.csv')
        except:    
            columns = ['task_id','type','level','PatientName','PatientID',
                       'StudyInstanceUID','StudyDate','StudyTime',
                       'SeriesInstanceUID','SeriesNumber',
                       'description','imgs','modality',
                       'source','destination','started','status','progress']  
            data = pd.DataFrame(columns = columns).set_index('task_id')                  

        self.data = data

        # Each device will have its separate handler. A placeholder is initialized here
        self.device_handlers = {}

    def _new_task(self, task_data):

        # Append new task to the database
        if self.data.index.empty:
            task_id = 0
        else:
            task_id = self.data.index.max() + 1
        
        columns = self.data.columns.drop('started','status')
        row = {col: task_data.get(col, '') for col in columns}
        row['started'] = datetime.now().strftime('%H:%M:%S')
        row['status'] = 'pending'
        row['progress'] = 0
        row['imgs'] = task_data['ImgsStudy'] if task_data['level'] == 'STUDY' else task_data['ImgsSeries']
        row['description'] = task_data['StudyDescription'] if task_data['level'] == 'STUDY' else task_data['StudyDescription'] + ' / ' + task_data['SeriesDescription']
        row['modality'] = task_data['ModalitiesInStudy'] if task_data['level'] == 'STUDY' else task_data['SeriesDescription']
        row = pd.DataFrame(row, index = [task_id])
        self.data = pd.concat([self.data, row])

        # Initialize a handler for this device
        if not (task_data['source'] in self.device_handlers):
            device_handler = DeviceTasksHandler()
            self.device_handlers[task_data['source']] = device_handler

        # Create the task for this device
        self.device_handlers[task_data['source']].manage_task(id = task_id, action = 'new', data = task_data)
    
    def manage_task(self, action, task_id = None, task_data = None):

        if action == 'new':
            self._new_task(task_data)
        elif action == 'delete':
            task_device = self.data.loc[task_id, 'source']
            self.device_handlers[task_device].manage_task(task_id, action)
            self.data.drop(task_id, inplace = True)
        elif action == 'retry':
            task_device = self.data.loc[task_id, 'source']
            self.device_handlers[task_device].manage_task(task_id, action)
            self.data.loc[task_id, 'started'] = datetime.now().strftime('%H:%M:%S')
        else:            
            task_device = self.data.loc[task_id, 'source']
            self.device_handlers[task_device].manage_task(task_id, action)

    def get_task_status(self, task_id):
        
        task_device = self.data.loc[task_id, 'source']
        device_handler = self.device_handlers[task_device]
        task_info = device_handler.tasks_list[task_id]
        status, progress = task_info['status'], task_info['progress']        
        self.data.loc[task_id,'progress'] = progress
        self.data.loc[task_id,'status'] = status

        return self.data.loc[task_id,'status']
    
    def get_tasks_table(self):

        data = []

        for task_id, task_data in self.data.iterrows():

            # Update task status         
            try:
                self.get_task_status(task_id) 
            except:
                logger.debug(f"get_task_table: failed at task id {task_id}")                
            row = task_data.to_dict()
            row['task_id'] = task_id
            data.append(row)

        return data        
    
class CheckStorageManager():

    def __init__(self):

        # Initialize progress and status
        self.progress = 0
        self.status = 'Desocupado'


    def find_missing_series(self, device_name, studydate):

        with application.app_context():
            device = Device.query.get(device_name)
            pacs = Device.query.get('PACS')
        assert device  
        device = {attr:getattr(device, attr) for attr in ["ae_title","port","address","imgs_study","imgs_series"]}
        pacs = {attr:getattr(pacs, attr) for attr in ["ae_title","port","address","imgs_study","imgs_series"]}

        # Build the data for the dicom query
        qr = {'StudyDate':  studydate}        
        rs = {'PatientName':'',
            'PatientID': '',
            'StudyTime': '',
            'StudyDescription': '',
            device["imgs_study"]: ''}
        
        # Start a DICOM AE to perform C-FIND operations on the device
        with application.app_context():
            ae = DicomInterface(ae_title = Device.query.get('__local_store_SCP__').ae_title)          

        # Query studies and series in the target device
        self.status = 'Buscando estudios en el dispositivo...'
        studies = ae.query_studies_in_device(device, qr, rs)

        # Get series for each study
        rs = {'SeriesNumber':'',
            'SeriesDate': '',
            'SeriesTime': '',
            'SeriesDescription': '',
            'Modality':'',
            device['imgs_series']: ''}
        
        # Search series in the device
        self.status = 'Buscando series en el dispositivo...'
        series_in_device = []        
        for idx, study in enumerate(studies):
            # Update progress
            self.progress = idx / len(studies)      

            # Query series in this study
            series_rsp = ae.query_series_in_study(device, study.StudyInstanceUID, responses = rs)
            
            # Add study information
            for series in series_rsp:
                for field in ['PatientName','PatientID','StudyDescription','StudyInstanceUID','StudyDate','StudyTime']:
                    try:
                        value = getattr(study, field)
                    except:
                        value = ''
                    setattr(series, field, value)

            series_in_device.extend(series_rsp)

        # Release connection with the device
        ae.release_connections()

        # Apply filters
        series_in_device = list(filter(lambda x: self.series_filter(x, device_name), series_in_device))

        # PACS connection
        with application.app_context():
            ae_pacs = DicomInterface(ae_title = Device.query.get('__local_store_SCP__').ae_title)
        
        # Check if each series exists in PACS with the same number of images
        self.status = 'Buscando series en el PACS...' 
        missing_series = []
        for idx, series in enumerate(series_in_device):
            # Update progress
            self.progress = idx / len(series_in_device)   
            
            qr = {'StudyInstanceUID': series.StudyInstanceUID, 
                'SeriesInstanceUID': series.SeriesInstanceUID,
                'QueryRetrieveLevel':'SERIES',
                pacs['imgs_series']: ''}
            series_in_pacs = ae_pacs.query_device(pacs, qr)

            try:
                series_in_pacs = series_in_pacs[0]
                if not device['imgs_series'] == 'Unknown':          
                    assert series_in_pacs[pacs['imgs_series']].value == series[device['imgs_series']].value
            except Exception as e:
                missing_series.append(series)
        
        ae_pacs.release_connections()

        # Reset status
        self.status = 'Desocupado'
        self.progress = 0

        return missing_series        
    
    def series_filter(self, ds, device_name):
            
        # Get filtering criteria from database
        with application.app_context():
            try:
                device = Device.query.get(device_name)
                assert device
                filters = device.basic_filters.all()
                logger.debug(f"found {filters} for {device}")
            except AssertionError:
                logger.error('device not found')
            except Exception as e:
                logger.error('database error')
                logger.error(repr(e))
                return False
        
        for f in filters:
            try:
                value = getattr(ds, f.field)                                
                if value == f.value:
                    logger.debug(f"rejected series with {f.field} == {value}")
                    return False                   
            except AttributeError:
                pass
        
        # El resonador 3T tiene algunas reglas más complicadas, por ahora
        # van a mano        
        if device_name == 'RESO 3T':
            try:
                if ds.NumberOfSeriesRelatedInstances == 0: return False
            except:
                pass
            try:
                if ((ds.SeriesNumber == '0') & (ds.NumberOfSeriesRelatedInstances == 1)): return False
            except:
                pass
            try:
                if ((ds.SeriesDescription == '') & (ds.NumberOfSeriesRelatedInstances == 1)): return False
            except AttributeError:
                pass

        return True