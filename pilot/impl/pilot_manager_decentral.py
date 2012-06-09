"""
Implementation of the ComputeDataService (decentral)

A Meta-Scheduling service for pilots (both PilotCompute and PilotData)
"""

import sys
import os
import time
import threading
import logging
import pdb
import Queue
import uuid
import traceback
import urlparse

import bigjob
import pilot
from bigjob import logger
from pilot.api import ComputeUnit, State
from pilot.impl.pilotdata_manager import PilotData, DataUnit
from pilot.impl.pilot_manager import ComputeDataService
#from pilot.coordination.advert import AdvertCoordinationAdaptor as CoordinationAdaptor
from pilot.coordination.redis import RedisCoordinationAdaptor as CoordinationAdaptor
from bigjob import bigjob, subjob, description

""" Loaded Module determines scheduler:
    
    bigdata.scheduler.data_compute_scheduler - selects random locations for PD and CUs
    bigdata.scheduler.data_compute_affinity_scheduler - considers affinity descriptions
    
"""
from pilot.scheduler.data_compute_affinity_scheduler import Scheduler

class ComputeDataServiceDecentral(ComputeDataService):
    """ ComputeDataService.
    
        The ComputeDataService is the application's interface to submit 
        ComputeUnits and PilotData/DataUnit to the Pilot-Manager 
        in the P* Model.
    """    
    CDS_ID_PREFIX="cds-"  


    def __init__(self, cds_url=None):
        """ Create a ComputeDataService object.

            Keyword arguments:
            cds_url -- Reconnect to an existing CDS (optional).
        """
        # Pilot Data
        self.data_units={}
        self.pilot_data_services=[]
        
        # Pilot Compute
        self.compute_units={}
        self.pilot_job_services=[]
            
        if cds_url == None:
            self.id=self.CDS_ID_PREFIX + str(uuid.uuid1())
            application_url = CoordinationAdaptor.get_base_url(pilot.application_id)
            self.url = CoordinationAdaptor.add_cds(application_url, self)            
        else:
            self.id = self.__get_cds_id(cds_url)
            self.url = cds_url
           
        
        

    def __get_cds_id(self, cds_url):
        start = cds_url.index(self.CDS_ID_PREFIX)
        end =cds_url.index("/", start)
        return cds_url[start:end]


    ###########################################################################
    # Pilot Compute    
    def add_pilot_compute_service(self, pjs):
        """ Add a PilotJobService to this CDS.

            Keyword arguments:
            pilotjob_services -- The PilotJob Service(s) to which this 
                                 Work Unit Service will connect.

            Return:
            Result
        """
        self.pilot_job_services.append(pjs)
        CoordinationAdaptor.update_cds(self.url, self)

    def remove_pilot_compute_service(self, pjs):
        """ Remove a PilotJobService from this CDS.

            Note that it won't cancel the PilotJobService, it will just no
            longer be connected to this WUS.

            Keyword arguments:
            pilotjob_services -- The PilotJob Service(s) to remove from this
                                 Work Unit Service. 

            Return:
            Result
        """
        self.pilot_job_services.remove(pjs)
        CoordinationAdaptor.update_cds(self.url, self)

    def submit_compute_unit(self, compute_unit_description):
        """ Submit a CU to this Compute Data Service.

            Keyword argument:
            cud -- The ComputeUnitDescription from the application

            Return:
            ComputeUnit object
        """
        cu = ComputeUnit(compute_unit_description, self)
        self.compute_units[cu.id]=cu
        self.cu_queue.put(cu)
        CoordinationAdaptor.update_cds(self.url, self)
        return cu
    
    
    ###########################################################################
    # Pilot Data     
    def add_pilot_data_service(self, pds):
        """ Add a PilotDataService 

            Keyword arguments:
            pds -- The PilotDataService to add.

            Return:
            None
        """
        raise NotImplementedError("Not implemented")
    
    
    def remove_pilot_data_service(self, pds):

        """ Remove a PilotDataService 
            
            Keyword arguments:
            pds -- The PilotDataService to remove 
            
            Return:
            None
        """
        raise NotImplementedError("Not implemented")
        
    
    def list_pilot_compute(self):
        """ List all pilot compute of CDS """
        return self.pilot_job_service
    
    
    def list_pilot_data(self):
        """ List all pilot data of CDS """
        raise NotImplementedError("Not implemented")
    
    
    def list_data_units(self):
        """ List all DUs of CDS """
        raise NotImplementedError("Not implemented")
    
    
    def get_data_unit(self, du_id):
        raise NotImplementedError("Not implemented")
    
    
    def submit_data_unit(self, data_unit_description):
        """ creates a data unit object and binds it to a physical resource (a pilotdata) """
        raise NotImplementedError("Not implemented")
    
    
    def cancel(self):
        """ Cancel the CDS. 
            All associated PC objects are deleted.            
            
            Keyword arguments:
            None

            Return:
            None
        """
        # terminate background thread
        self.stop.set()
        CoordinationAdaptor.delete_cds(self.url)
   
   
   
    def wait(self):
        """ Waits for CUs and DUs
            Return if all du's are running 
                   AND
                   cu's are done
            
        """
        try:
            logger.debug("### START WAIT ###")
            self.cu_queue.join()
            logger.debug("CU queue empty")        
            self.du_queue.join()
            logger.debug("DU queue empty")        
    
            for i in self.data_units.values():
                i.wait()
            logger.debug("DUs done")        
                
            for i in self.compute_units.values():
                i.wait()     
            logger.debug("CUs done")        
                   
            logger.debug("### END WAIT ###")
        except:
            logger.debug("Ctrl-c detected. Terminating ComputeDataService...")
            self.cancel()
            raise KeyboardInterrupt
                
        
    def get_state(self):
        return self.state
    
    
    def get_id(self):
        return str(self.id)
    
    
    def __del__(self):
        """ Make sure that background thread terminates"""
        self.cancel()
   
    
   
    
   