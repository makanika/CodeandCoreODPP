class ConductDatabaseRouter:
    route_app_labels = {'conduct'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'conduct'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'conduct'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        app_labels = {obj1._meta.app_label, obj2._meta.app_label}
        if app_labels & self.route_app_labels:
            return app_labels == self.route_app_labels
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'conduct'
        if db == 'conduct':
            return False
        return None