import unittest

from tools.database_operations import checked_target, client_command


class OperationBoundaryTests(unittest.TestCase):
    def test_cleanup_target_rejects_working_database_and_unscoped_names(self):
        name='energy_restore_test_'+'a'*32
        self.assertEqual(checked_target(name,'finnish_energy'),name)
        for value in ('finnish_energy','energy_restore_test_','energy_restore_test_'+'a'*32+';DROP DATABASE x',name.upper()):
            with self.assertRaises(ValueError):checked_target(value,'finnish_energy')
        with self.assertRaises(ValueError):checked_target(name,name)

    def test_client_arguments_do_not_embed_password(self):
        settings={'host':'127.0.0.1','port':5432,'user':'fixture_user','password':'secret_test_marker'}
        for mode in ('docker','local'):
            command=client_command(mode,'pg_dump',settings)
            self.assertNotIn(settings['password'],' '.join(command))
            self.assertEqual(command[-2:],['--username','fixture_user'])
