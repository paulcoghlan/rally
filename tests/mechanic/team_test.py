import os
from unittest import TestCase

from esrally import exceptions
from esrally.mechanic import team

current_dir = os.path.dirname(os.path.abspath(__file__))


class CarLoaderTests(TestCase):
    def __init__(self, args):
        super().__init__(args)
        self.team_dir = None
        self.loader = None

    def setUp(self):
        self.team_dir = os.path.join(current_dir, "data")
        self.loader = team.CarLoader(self.team_dir)

    def test_lists_car_names(self):
        # contrary to the name this assertion compares contents but does not care about order.
        self.assertCountEqual(
            ["default", "with_hook", "32gheap", "missing_cfg_base", "empty_cfg_base", "ea", "verbose", "multi_hook", "another_with_hook"],
            self.loader.car_names()
        )

    def test_load_known_car(self):
        car = team.load_car(self.team_dir, ["default"], car_params={"data_paths": ["/mnt/disk0", "/mnt/disk1"]})
        self.assertEqual("default", car.name)
        self.assertEqual([os.path.join(current_dir, "data", "cars", "v1", "vanilla", "templates")], car.config_paths)
        self.assertIsNone(car.root_path)
        self.assertDictEqual({
            "heap_size": "1g",
            "clean_command": "./gradlew clean",
            "data_paths": ["/mnt/disk0", "/mnt/disk1"]
        }, car.variables)
        self.assertEqual({}, car.env)
        self.assertIsNone(car.root_path)

    def test_load_car_with_mixin_single_config_base(self):
        car = team.load_car(self.team_dir, ["32gheap", "ea"])
        self.assertEqual("32gheap+ea", car.name)
        self.assertEqual([os.path.join(current_dir, "data", "cars", "v1", "vanilla", "templates")], car.config_paths)
        self.assertIsNone(car.root_path)
        self.assertEqual({
            "heap_size": "32g",
            "clean_command": "./gradlew clean",
            "assertions": "true"
        }, car.variables)
        self.assertEqual({"JAVA_TOOL_OPTS": "A B C D E F"}, car.env)
        self.assertIsNone(car.root_path)

    def test_load_car_with_mixin_multiple_config_bases(self):
        car = team.load_car(self.team_dir, ["32gheap", "ea", "verbose"])
        self.assertEqual("32gheap+ea+verbose", car.name)
        self.assertEqual([
            os.path.join(current_dir, "data", "cars", "v1", "vanilla", "templates"),
            os.path.join(current_dir, "data", "cars", "v1", "verbose_logging", "templates"),
        ], car.config_paths)
        self.assertIsNone(car.root_path)
        self.assertEqual({
            "heap_size": "32g",
            "clean_command": "./gradlew clean",
            "verbose_logging": "true",
            "assertions": "true"
        }, car.variables)
        self.assertEqual({"JAVA_TOOL_OPTS": "A B C D E F G H I"}, car.env)

    def test_load_car_with_install_hook(self):
        car = team.load_car(self.team_dir, ["default", "with_hook"], car_params={"data_paths": ["/mnt/disk0", "/mnt/disk1"]})
        self.assertEqual("default+with_hook", car.name)
        self.assertEqual([
            os.path.join(current_dir, "data", "cars", "v1", "vanilla", "templates"),
            os.path.join(current_dir, "data", "cars", "v1", "with_hook", "templates"),
        ], car.config_paths)
        self.assertEqual(os.path.join(current_dir, "data", "cars", "v1", "with_hook"), car.root_path)
        self.assertDictEqual({
            "heap_size": "1g",
            "clean_command": "./gradlew clean",
            "data_paths": ["/mnt/disk0", "/mnt/disk1"]
        }, car.variables)
        self.assertEqual({}, car.env)

    def test_load_car_with_multiple_bases_referring_same_install_hook(self):
        car = team.load_car(self.team_dir, ["with_hook", "another_with_hook"])
        self.assertEqual("with_hook+another_with_hook", car.name)
        self.assertEqual([
            os.path.join(current_dir, "data", "cars", "v1", "vanilla", "templates"),
            os.path.join(current_dir, "data", "cars", "v1", "with_hook", "templates"),
            os.path.join(current_dir, "data", "cars", "v1", "verbose_logging", "templates")
        ], car.config_paths)
        self.assertEqual(os.path.join(current_dir, "data", "cars", "v1", "with_hook"), car.root_path)
        self.assertDictEqual({
            "heap_size": "16g",
            "clean_command": "./gradlew clean",
            "verbose_logging": "true"
        }, car.variables)
        self.assertEqual({}, car.env)


    def test_raises_error_on_unknown_car(self):
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            team.load_car(self.team_dir, ["don_t-know-you"])
        self.assertRegex(ctx.exception.args[0], r"Unknown car \[don_t-know-you\]. List the available cars with [^\s]+ list cars.")

    def test_raises_error_on_empty_config_base(self):
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            team.load_car(self.team_dir, ["empty_cfg_base"])
        self.assertEqual("At least one config base is required for car ['empty_cfg_base']", ctx.exception.args[0])

    def test_raises_error_on_missing_config_base(self):
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            team.load_car(self.team_dir, ["missing_cfg_base"])
        self.assertEqual("At least one config base is required for car ['missing_cfg_base']", ctx.exception.args[0])

    def test_raises_error_if_more_than_one_different_install_hook(self):
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            team.load_car(self.team_dir, ["multi_hook"])
        self.assertEqual("Invalid car: ['multi_hook']. Multiple bootstrap hooks are forbidden.", ctx.exception.args[0])


class PluginLoaderTests(TestCase):
    def __init__(self, args):
        super().__init__(args)
        self.loader = None

    def setUp(self):
        self.loader = team.PluginLoader(os.path.join(current_dir, "data"))

    def test_lists_plugins(self):
        self.assertCountEqual(
            [
                team.PluginDescriptor(name="complex-plugin", config="config-a"),
                team.PluginDescriptor(name="complex-plugin", config="config-b"),
                team.PluginDescriptor(name="my-analysis-plugin", core_plugin=True),
                team.PluginDescriptor(name="my-ingest-plugin", core_plugin=True)
            ], self.loader.plugins())

    def test_loads_core_plugin(self):
        self.assertEqual(team.PluginDescriptor(name="my-analysis-plugin", core_plugin=True),
                         self.loader.load_plugin("my-analysis-plugin", None))

    def test_cannot_load_plugin_with_missing_config(self):
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            self.loader.load_plugin("my-analysis-plugin", ["missing-config"])
        self.assertRegex(ctx.exception.args[0], r"Plugin \[my-analysis-plugin\] does not provide configuration \[missing-config\]. List the"
                                                r" available plugins and configurations with [^\s]+ list elasticsearch-plugins "
                                                r"--distribution-version=VERSION.")

    def test_loads_community_plugin_without_configuration(self):
        self.assertEqual(team.PluginDescriptor("my-community-plugin"), self.loader.load_plugin("my-community-plugin", None))

    def test_cannot_load_community_plugin_with_missing_config(self):
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            self.loader.load_plugin("my-community-plugin", "some-configuration")
        self.assertRegex(ctx.exception.args[0], r"Unknown plugin \[my-community-plugin\]. List the available plugins with [^\s]+ list "
                                                r"elasticsearch-plugins --distribution-version=VERSION.")

    def test_loads_configured_plugin(self):
        plugin = self.loader.load_plugin("complex-plugin", ["config-a", "config-b"])
        self.assertEqual("complex-plugin", plugin.name)
        self.assertCountEqual(["config-a", "config-b"], plugin.config)

        expected_root_path = os.path.join(current_dir, "data", "plugins", "v1", "complex_plugin")

        self.assertEqual(expected_root_path, plugin.root_path)
        # order does matter here! We should not swap it
        self.assertListEqual([
            os.path.join(expected_root_path, "default", "templates"),
            os.path.join(expected_root_path, "special", "templates"),
        ], plugin.config_paths)

        self.assertEqual({
            "foo": "bar",
            "baz": "foo",
            "var": "0",
            "hello": "true"
        }, plugin.variables)


class BootstrapHookHandlerTests(TestCase):
    class UnitTestComponentLoader:
        def __init__(self, root_path, component_entry_point, recurse):
            self.root_path = root_path
            self.component_entry_point = component_entry_point
            self.recurse = recurse
            self.registration_function = None

        def load(self):
            return self.registration_function

    class UnitTestHook:
        def __init__(self, phase="post_install"):
            self.phase = phase
            self.call_counter = 0

        def post_install_hook(self, config_names, variables, **kwargs):
            self.call_counter += variables["increment"]

        def register(self, handler):
            # we can register multiple hooks here
            handler.register(self.phase, self.post_install_hook)
            handler.register(self.phase, self.post_install_hook)

    def test_loads_module(self):
        plugin = team.PluginDescriptor("unittest-plugin")
        hook = BootstrapHookHandlerTests.UnitTestHook()
        handler = team.BootstrapHookHandler(plugin, loader_class=BootstrapHookHandlerTests.UnitTestComponentLoader)

        handler.loader.registration_function = hook
        handler.load()

        handler.invoke("post_install", variables={"increment": 4})

        # we registered our hook twice. Check that it has been called twice.
        self.assertEqual(hook.call_counter, 2 * 4)

    def test_cannot_register_for_unknown_phase(self):
        plugin = team.PluginDescriptor("unittest-plugin")
        hook = BootstrapHookHandlerTests.UnitTestHook(phase="this_is_an_unknown_install_phase")
        handler = team.BootstrapHookHandler(plugin, loader_class=BootstrapHookHandlerTests.UnitTestComponentLoader)

        handler.loader.registration_function = hook
        with self.assertRaises(exceptions.SystemSetupError) as ctx:
            handler.load()
        self.assertEqual("Unknown bootstrap phase [this_is_an_unknown_install_phase]. Valid phases are: ['post_install', 'post_launch'].",
                         ctx.exception.args[0])
