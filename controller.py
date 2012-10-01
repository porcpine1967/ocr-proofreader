#!/usr/bin/python env


from models import Project

class ProofreaderController(object):
    def __init__(self):
        self.project = None

    def new(self, project_directory):
        self.project = Project(project_directory)
        self.project.create()
        self.status = self.project.status

    def __getattr__(self, name):
        if name == 'status':
            if self.project:
                return self.project.status
            else:
                return Project.STATUS_UNINITIALIZED
        else:
            raise AttributeError("ProofreaderController has no attribute '{}'".format(name))
