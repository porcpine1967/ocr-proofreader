#!/usr/bin/env python

from ConfigParser import ConfigParser
import os

STATE_UNINITIALIZED = 'uninitialized'
STATE_NEEDS_CONFIG = 'needs_config'
STATE_NEEDS_METADATA = 'needs_metadata'
STATE_NEEDS_PDFS = 'needs_pdfs'
STATE_NEEDS_IMAGES = 'needs_images'
STATE_NEEDS_TEXT = 'needs_text'
STATE_NEEDS_CLEAN_1 = 'needs_clean_1'
STATE_NEEDS_PROPER_NAME_CHECK = 'needs_proper_name_check'
STATE_NEEDS_CLEAN_2 = 'needs_clean_2'
STATE_NOT_ALL_LINES_GOOD = 'not_all_lines_good'
STATE_DONE = 'done'
STATE_UNKNOWN = 'unknown'

class Project(object):
    """ Represents the project and its status."""
    def __init__(self, project_directory):
        self.project_directory = project_directory
        if not project_directory:
            self.status = STATE_UNINITIALIZED
        else:
            self.directory = '{}{}.project'.format(project_directory, os.sep)
            self.conf_path = '{}{}book.cnf'.format(self.directory, os.sep)
            self._set_current_status()

    def _set_current_status(self):
        self.status = STATE_UNKNOWN   
        if not os.path.exists(self.project_directory):
            self.status = STATE_UNINITIALIZED
            return 
        self.config = ConfigParser()
        # Load config if it already exists
        if os.path.exists(self.conf_path):
            self.config.read(self.conf_path)
            self.current_status = self.config.get('process', 'current_status')
        else:
            self.status = STATE_NEEDS_CONFIG 
            return 


    def create(self, project_directory):
        """ Sets up what needs to be set up.
            Should only be called if current state is STATE_UNINITIALIZED
        """
        # redo setup based on passed project directory
        self.project_directory = project_directory
        self.directory = '{}{}.project'.format(project_directory, os.sep)
        self.conf_path = '{}{}book.cnf'.format(self.directory, os.sep)

        # make sure the project directory exists
        if not os.path_exists(self.directory):
            os.makedirs(self.directory)
        
        # make sure our config is loaded
        if not self.config:
            self.config = ConfigParser()
            if os.path_exists(self.conf_path):
                self.config.read(self.conf_path)

        # make sure all the sections of the config exist
        sections = (
            'extract_text',
            'metadata',
            'process',
        )   

        for section in sections:
            if not self.config.has_section(section):
                self.config.add_section(section)

        # set current status if it hasn't been set
        if not self.config.has_option('process', 'current_status'):
            self.config.set('process', 'current_status', STATE_NEEDS_METADATA)

        metadata = (
            'author',
            'title'
        )
        # set metadata if it hasn't been set
        for data in metadata:
            if not self.config.get('metadata', data):
                self.config.set('metadata', data, '')

        # write the config
        self.write_config()

    def write_config(self):
        with open(self.conf_path, 'wb') as f:
            self.config.write(f)

    def get_metadata(self):
        """ Returns dictionary of metadata. """
        metadata = {
            'author': '',
            'title': '',
        }
        for data in metadata.keys():
            try:
                metadata[data] = self.config.get('metadata', data)
            except:
                pass
        return metadata

    def set_metadata(self, dict_):
        """ Sets metadata for book in conf.
        Advances status if valid. 
        """
        for key, value in dict_.items():
            self.config.set('metadata', key, value)                                    
        if self.status == STATE_NEEDS_METADATA and \
            self.config.get('metadata', 'author') and \
            self.config.get('metadata', 'title'):

            self.config.set('process', STATE_NEED_PDFS)

        self.write_config()

        self._set_current_status() 
