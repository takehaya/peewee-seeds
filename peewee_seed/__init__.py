import importlib
import json
import os

import yaml


__version__ = "0.1.8"


class PeeweeSeed(object):
    def __init__(self, db=None, path=None, fixture_files=None):
        self.db = db
        self.path = path
        self.fixture_files = fixture_files

    # setter
    def set_database(self, db):
        self.db = db

    def set_path(self, path):
        self.path = path

    def set_fixture_files(self, fixture_files):
        self.fixture_files = fixture_files

    # getter
    def get_tables(self, models_path_list=None, fixture_data=None):
        if models_path_list is None:
            _, models_path_list = self.load_fixtures(fixture_data)
        model_table = []
        for models_str in models_path_list:
            model = self.__get_tablemodel_class(models_str)
            if not (model[0] in model_table):
                model_table.append(model[0])

        return model_table

    # db move
    def create_table_all(self, models_path_list=None, not_exist_create=True):
        tables_list = self.get_tables(models_path_list)
        self.__create_table(tables_list, not_exist_create)

    def drop_table_all(self, models_path_list=None, foreign_key_checks=False):
        if foreign_key_checks:
            self.db.execute_sql("SET FOREIGN_KEY_CHECKS=0;")

        tables_list = self.get_tables(models_path_list)
        self.db.drop_tables(tables_list)

        if foreign_key_checks:
            self.db.execute_sql("SET FOREIGN_KEY_CHECKS=1;")

    def __create_table(self, tables, not_exist_create=True):
        self.db.create_tables(tables, safe=not_exist_create)

    def __drop_table(self, tables):
        self.db.drop_tables(tables)

    # fixture loads
    # fixtures read data
    def load_fixture_files(self, files=None, encoding='utf-8'):
        fixtures = []

        if self.path is None:
            raise Exception("your set path data")

        if files is None:
            files = self.fixture_files

        if not isinstance(self.path, list):
            paths = [self.path]

        for path in paths:
            for file in files:
                fixture_path = os.path.join(path, file)
                if not os.path.exists(fixture_path):
                    continue

                with open(fixture_path, "r", encoding=encoding) as f:
                    if file.endswith(".yaml") or file.endswith(".yml"):
                        data = yaml.safe_load(f)
                    elif file.endswith(".json"):
                        data = json.load(f)
                    else:
                        continue
                    fixtures.append(data)
        return fixtures

    # fixture one of load
    @staticmethod
    def load_fixture(fixture):
        fields = []
        models = []
        for data in fixture:
            if "model" in data:
                _, class_name = data["model"].rsplit(".", 1)
                if class_name in fields:
                    fields[class_name].append(data["fields"])
                else:
                    models.append(data["model"])
                    fields.append({class_name: data["fields"]})
        return fields, models

    @staticmethod
    def __get_tablemodel_class(model_str):
        module_name, class_name = model_str.rsplit(".", 1)
        module = importlib.import_module(module_name)
        model = getattr(module, class_name)

        return model, class_name

    # fixtures mul of load
    def load_fixtures(self, fixture_data=None):

        if fixture_data is None:
            fixture_data = self.load_fixture_files(self.fixture_files)

        fixtures_fields = []
        fixtures_models = []
        for fixture in fixture_data:
            data, models = self.load_fixture(fixture)
            fixtures_fields.append(data)
            for model in models:
                if not (model in fixtures_models):
                    fixtures_models.append(model)

        return fixtures_fields, fixtures_models

    # fixtures data to db input
    def db_data_input(self, fixture_data=None, foreign_key_checks=False):

        if foreign_key_checks:
            self.db.execute_sql("SET FOREIGN_KEY_CHECKS=0;")

        if fixture_data is None:
            fixture_data = self.load_fixture_files(self.fixture_files)
        fields, models_list = self.load_fixtures(fixture_data)
        try:
            with self.db.transaction():
                for model_str in models_list:
                    model, class_name = self.__get_tablemodel_class(model_str)
                    flatfield = []
                    for field in fields:
                        for f in field:
                            if class_name in f:
                                flatfield.append(f[class_name])
                    model.insert_many(flatfield).execute()

        except Exception:
            self.db.rollback()
            raise Exception("Error. db rollback")

        if foreign_key_checks:
            self.db.execute_sql("SET FOREIGN_KEY_CHECKS=1;")
