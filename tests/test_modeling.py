"""UUID boundaries, deterministic model identity and bounded secret-safe dbt invocation."""

import json
from contextlib import chdir
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from ingestion.modeling import execute_dbt, model_identity


class ModelingTests(unittest.TestCase):
    def test_relative_and_canonical_roots_produce_the_same_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'models').mkdir()
            (root/'models/dbt_project.yml').write_text('name: fixture\n',encoding='utf-8')
            release=uuid4()
            with patch('ingestion.modeling.importlib.metadata.version',return_value='fixture'):
                expected=model_identity(root.resolve(),release)
                with chdir(root):
                    self.assertEqual(model_identity(Path('.'),release),expected)

    def test_release_uuid_rejected_before_process_or_database_work(self):
        with patch('ingestion.modeling.subprocess.run') as run:
            with self.assertRaises(ValueError):
                execute_dbt(Path.cwd(),"x';drop schema",Path('unused'))
        run.assert_not_called()

    def test_identity_tracks_model_changes_and_release_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'models').mkdir()
            project=root/'models/dbt_project.yml';project.write_text('name: fixture\n',encoding='utf-8')
            release=uuid4()
            with patch('ingestion.modeling.importlib.metadata.version',return_value='fixture'):
                first=model_identity(root,release)[1]
                self.assertNotEqual(first,model_identity(root,uuid4())[1])
                project.write_text('name: changed\n',encoding='utf-8')
                self.assertNotEqual(first,model_identity(root,release)[1])

    def test_password_is_environment_only_and_redacted_from_console(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'run'
            options={'password':'fixture-secret','host':'127.0.0.1','port':5432,'dbname':'fixture','user':'fixture'}
            with patch('ingestion.modeling.subprocess.run',return_value=Mock(returncode=1,stdout='fixture-secret',stderr='')) as run:
                result=execute_dbt(root,uuid4(),output,options=options)
            self.assertEqual(result['exit_code'],1)
            self.assertNotIn('fixture-secret',json.dumps(run.call_args.args))
            self.assertNotIn('fixture-secret',(output/'console.txt').read_text(encoding='utf-8'))
            self.assertEqual(run.call_args.kwargs['env']['DBT_ENV_SECRET_PASSWORD'],'fixture-secret')

    def test_dbt_timeout_is_bounded_and_has_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            options={'password':'fixture-secret','host':'127.0.0.1','port':5432,'dbname':'fixture','user':'fixture'}
            with patch('ingestion.modeling.subprocess.run',side_effect=subprocess.TimeoutExpired('dbt',300)):
                result=execute_dbt(Path(temporary),uuid4(),Path(temporary)/'run',options=options)
            self.assertEqual(result['error_code'],'DBT_CHILD_TIMEOUT')
