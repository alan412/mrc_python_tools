import inspect
import pathlib
import sys

from absl import app
from absl import flags
from absl import logging

import hal
import hal.simulation
import ntcore
import pyfrc
import wpilib
import wpilib.counter
import wpilib.drive
import wpilib.event
import wpilib.interfaces
import wpilib.shuffleboard
import wpilib.simulation
import wpimath
import wpimath.controller
import wpimath.estimator
import wpimath.filter
import wpimath.geometry
import wpimath.interpolation
import wpimath.kinematics
import wpimath.optimization
import wpimath.path
import wpimath.spline
import wpimath.system
import wpimath.system.plant
import wpimath.trajectory
import wpimath.trajectory.constraint
import wpimath.units
import wpinet
import wpiutil

import blocks
import python_util


FLAGS = flags.FLAGS

flags.DEFINE_string('output_directory', None, 'The directory where output should be written.')


def _generatePythonUtils(blocks_generator: blocks.BlocksGenerator):
  ts_file = open(f'{FLAGS.output_directory}/generate_blocks/blocks/utils/generated/python.ts', 'w', encoding='utf-8')
  print('// This file was generated. Do not edit!\n', file=ts_file)
  print('// Blocks constants and utilities.\n', file=ts_file)
  code = blocks_generator.generateConstants()
  print(code, file=ts_file)
  print('', file=ts_file)
  code = blocks_generator.generateGetAliasFunction()
  print(code, file=ts_file)
  print('', file=ts_file)
  code = blocks_generator.generateGetAllowedTypesFunction()
  print(code, file=ts_file)
  ts_file.close()


def _generateBlocksForModule(module, blocks_generator: blocks.BlocksGenerator, initialize_function_names, toolbox_function_names, ts_file_names):
  module_name = blocks.getModuleName(module)

  import_lines_set = set()
  initialize_lines = []
  toolbox_blocks = []

  # Module variable blocks.
  dict_type_to_getter_var_names = {}
  dict_type_to_setter_var_names = {}
  for key, value in inspect.getmembers(module, python_util.isNothing):
    if not python_util.isModuleVariableReadable(module, key, value):
      continue
    var_type = blocks.getClassName(type(value))
    list = dict_type_to_getter_var_names.get(var_type)
    if not list:
      list = []
      dict_type_to_getter_var_names.update({var_type: list})
    list.append(key)
    if python_util.isModuleVariableWritable(module, key, value):
      list = dict_type_to_setter_var_names.get(var_type)
      if not list:
        list = []
        dict_type_to_setter_var_names.update({var_type: list})
      list.append(key)
  for var_type, getter_var_names in dict_type_to_getter_var_names.items():
    getter_var_names.sort()
    setter_var_names = dict_type_to_setter_var_names.get(var_type, [])
    setter_var_names.sort()
    blocks_generator.generateBlocksForModuleOrClassVariables(
        module_name, None, var_type, getter_var_names, setter_var_names,
        import_lines_set, initialize_lines, toolbox_blocks)

  # Module function blocks
  for key, value in inspect.getmembers(module, inspect.isroutine):
    if not python_util.isFunction(module, key, value):
      continue
    blocks_generator.generateBlockForModuleFunction(
        module, key, value, toolbox_blocks)

  # Enum blocks
  for key, value in inspect.getmembers(module, python_util.isEnum):
    blocks_generator.generateBlocksForEnum(
        value, import_lines_set, initialize_lines, toolbox_blocks)

  # Generate a function that does the initialization.
  (initialize_function_code, initialize_function_name) = (
      blocks_generator.generateInitializeFunction(initialize_lines))

  # Generate a function that provides the category for the toolbox.
  (toolbox_function_code, toolbox_function_name) = (
      blocks_generator.generateGetToolboxCategoryFunction(
          module, None, toolbox_blocks, import_lines_set))

  ts_file_name = f'module_{module_name}.ts'
  ts_file = open(f'{FLAGS.output_directory}/generate_blocks/blocks/generated/{ts_file_name}', 'w', encoding='utf-8')
  print('// This file was generated. Do not edit!\n', file=ts_file)
  if len(import_lines_set) > 0:
    for import_line in sorted(import_lines_set):
      print(import_line, file=ts_file)
    print('', file=ts_file)
  print(f'// Blocks for module {module_name}\n', file=ts_file)
  print(initialize_function_code, file=ts_file)
  print('', file=ts_file)
  print(toolbox_function_code, file=ts_file)
  ts_file.close()
  initialize_function_names[module_name] = initialize_function_name
  toolbox_function_names[module_name] = toolbox_function_name
  ts_file_names[module_name] = ts_file_name


def _generateBlocksForModules(modules, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names):
  set_of_modules = set()
  for module in modules:
    set_of_modules.add(module)
  for module in set_of_modules:
    module_name = blocks.getModuleName(module)
    if module_name.startswith('ntcore'):
      continue
    if module_name.startswith('wpinet'):
      continue
    if module_name.startswith('wpiutil'):
      continue
    _generateBlocksForModule(module, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names)
  

def _generateBlocksForClass(cls, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names):
  if python_util.isEnum(cls):
    return
  module_name = blocks.getModuleName(cls.__module__)
  class_name = blocks.getClassName(cls)

  import_lines_set = set()
  initialize_lines = []
  toolbox_blocks = []

  # Class variable blocks.
  dict_type_to_getter_var_names = {}
  dict_type_to_setter_var_names = {}
  for key, value in inspect.getmembers(cls, python_util.isNothing):
    if not python_util.isClassVariableReadable(cls, key, value):
      continue
    var_type = blocks.getClassName(type(value))
    list = dict_type_to_getter_var_names.get(var_type)
    if not list:
      list = []
      dict_type_to_getter_var_names.update({var_type: list})
    list.append(key)
    if python_util.isClassVariableWritable(cls, key, value):
      list = dict_type_to_setter_var_names.get(var_type)
      if not list:
        list = []
        dict_type_to_setter_var_names.update({var_type: list})
      list.append(key)
  for var_type, getter_var_names in dict_type_to_getter_var_names.items():
    getter_var_names.sort()
    setter_var_names = dict_type_to_setter_var_names.get(var_type, [])
    setter_var_names.sort()
    blocks_generator.generateBlocksForModuleOrClassVariables(
        module_name, class_name, var_type, getter_var_names, setter_var_names,
        import_lines_set, initialize_lines, toolbox_blocks)

  # Instance variable blocks
  dict_type_to_getter_var_names = {}
  dict_type_to_setter_var_names = {}
  members = {}
  for key, value in inspect.getmembers(cls, inspect.isdatadescriptor):
    if not python_util.isInstanceVariableReadable(cls, key, value):
      continue
    members[key] = value
    var_type = python_util.getVarTypeFromGetter(value.fget)
    list = dict_type_to_getter_var_names.get(var_type)
    if not list:
      list = []
      dict_type_to_getter_var_names.update({var_type: list})
    list.append(key)
    if python_util.isInstanceVariableWritable(cls, key, value):
      list = dict_type_to_setter_var_names.get(var_type)
      if not list:
        list = []
        dict_type_to_setter_var_names.update({var_type: list})
      list.append(key)
  for var_type, getter_var_names in dict_type_to_getter_var_names.items():
    getter_var_names.sort()
    setter_var_names = dict_type_to_setter_var_names.get(var_type, [])
    setter_var_names.sort()
    blocks_generator.generateBlocksForInstanceVariables(
        cls, var_type, getter_var_names, setter_var_names, members,
        import_lines_set, initialize_lines, toolbox_blocks)

  # Constructor blocks
  for key, value in inspect.getmembers(cls, python_util.mightBeConstructor):
    if not python_util.isConstructor(cls, key, value):
      continue
    blocks_generator.generateBlockForClassOrInstanceFunction(
        cls, key, value, toolbox_blocks)

  # Function blocks
  for key, value in inspect.getmembers(cls, inspect.isroutine):
    if not python_util.isFunction(cls, key, value):
      continue
    blocks_generator.generateBlockForClassOrInstanceFunction(
        cls, key, value, toolbox_blocks)

  # Enum blocks
  for key, value in inspect.getmembers(cls, python_util.isEnum):
    if not blocks.getClassName(value).startswith(class_name):
      continue
    blocks_generator.generateBlocksForEnum(
        value, import_lines_set, initialize_lines, toolbox_blocks)

  # Generate a function that does the initialization.
  (initialize_function_code, initialize_function_name) = (
      blocks_generator.generateInitializeFunction(initialize_lines))

  # Generate a function that provides the category for the toolbox.
  (toolbox_function_code, toolbox_function_name) = (
      blocks_generator.generateGetToolboxCategoryFunction(
          None, cls, toolbox_blocks, import_lines_set))

  ts_file_name = f'class_{class_name}.ts'
  ts_file = open(f'{FLAGS.output_directory}/generate_blocks/blocks/generated/{ts_file_name}', 'w', encoding='utf-8')
  print('// This file was generated. Do not edit!\n', file=ts_file)
  if len(import_lines_set) > 0:
    for import_line in import_lines_set:
      print(import_line, file=ts_file)
    print('', file=ts_file)
  print(f'// Blocks for class {class_name}\n', file=ts_file)
  print(initialize_function_code, file=ts_file)
  print('', file=ts_file)
  print(toolbox_function_code, file=ts_file)
  ts_file.close()
  initialize_function_names[class_name] = initialize_function_name
  toolbox_function_names[class_name] = toolbox_function_name
  ts_file_names[class_name] = ts_file_name


def _generateBlocksForClasses(classes, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names):
  set_of_classes = set()
  for cls in classes:
    for c in inspect.getmro(cls):
      if python_util.isBuiltInClass(c):
        break
      set_of_classes.add(c)
  for cls in set_of_classes:
    module_name = blocks.getModuleName(cls.__module__)
    if module_name.startswith('ntcore'):
      continue
    if module_name.startswith('wpinet'):
      continue
    if module_name.startswith('wpiutil'):
      continue
    _generateBlocksForClass(cls, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names)


def _writeInitializeFile(initialize_function_names, ts_file_names):
  ts_file = open(f'{FLAGS.output_directory}/generate_blocks/blocks/utils/generated/initialize.ts', 'w', encoding='utf-8')
  print('// This file was generated. Do not edit!\n', file=ts_file)
  for key in sorted(ts_file_names.keys()):
    ts_file_name = ts_file_names[key]
    ts_file_name_without_suffix = ts_file_name[:ts_file_name.rfind('.')]
    ts_module = key.replace('.', '_')
    print(
        f'import * as {ts_module} from \'../../generated/{ts_file_name_without_suffix}\';',
        file=ts_file)
  print('', file=ts_file)
  print(f'export function initialize() {{', file=ts_file)
  for key in sorted(initialize_function_names.keys()):
    ts_module = key.replace('.', '_')
    print(f'  {ts_module}.{initialize_function_names[key]}();', file=ts_file)
  print('}', file=ts_file)
  ts_file.close()


def _buildCategoryTree(keys: list[str]) -> dict[str, dict]:
  trunk = {}
  for key in keys:
    tree = trunk
    for part in key.split('.'):
      if part not in tree:
        tree[part] = {}
      tree = tree[part]
  return trunk


def _organizeToolbox(parent, tree, spaces, toolbox_function_names) -> str:
  toolbox = ''
  for part in sorted(tree.keys()):
    if parent:
      key = parent + '.' + part
    else:
      key = part

    if key in toolbox_function_names:
      ts_module = key.replace('.', '_')
      toolbox += f'    {spaces}{ts_module}.{toolbox_function_names[key]}(['
    else:
      toolbox += (
        f'    {spaces}{{ kind: "category", name: "{part}", '
        'contents: [')
    r = _organizeToolbox(key, tree[part], spaces + '  ', toolbox_function_names)
    if r:
      toolbox += f'\n{r}    {spaces}'
    if key in toolbox_function_names:
      toolbox += ']),\n'
    else:
      toolbox += ']},\n'
  return toolbox


def _writeToolboxFile(toolbox_function_names, ts_file_names):
  category_tree = _buildCategoryTree(toolbox_function_names.keys())
  toolbox = _organizeToolbox('', category_tree, '', toolbox_function_names)
  ts_file = open(f'{FLAGS.output_directory}/generate_blocks/toolbox/generated/toolbox.ts', 'w', encoding='utf-8')
  print('// This file was generated. Do not edit!\n', file=ts_file)
  for key in sorted(ts_file_names.keys()):
    ts_file_name = ts_file_names[key]
    ts_file_name_without_suffix = ts_file_name[:ts_file_name.rfind('.')]
    ts_module = key.replace('.', '_')
    print(
        f'import * as {ts_module} from \'../../blocks/generated/{ts_file_name_without_suffix}\';',
        file=ts_file)
  print('', file=ts_file)
  print(f'export function getToolboxCategories() {{', file=ts_file)
  print('  return [', file=ts_file)
  print(toolbox, end='', file=ts_file)
  print('  ];', file=ts_file)
  print('}', file=ts_file)
  ts_file.close()


def main(argv):
  del argv  # Unused.

  if not FLAGS.output_directory:
    logging.error(f'You must specify the --output_directory argument')
    return

  pathlib.Path(f'{FLAGS.output_directory}/generate_blocks/blocks/generated').mkdir(parents=True, exist_ok=True)
  pathlib.Path(f'{FLAGS.output_directory}/generate_blocks/blocks/utils/generated').mkdir(parents=True, exist_ok=True)
  pathlib.Path(f'{FLAGS.output_directory}/generate_blocks/toolbox/generated').mkdir(parents=True, exist_ok=True)

  root_modules = [
    hal,
    hal.simulation,
    ntcore,
    wpilib,
    wpilib.counter,
    wpilib.drive,
    wpilib.event,
    wpilib.interfaces,
    wpilib.shuffleboard,
    wpilib.simulation,
    wpimath,
    wpimath.controller,
    wpimath.estimator,
    wpimath.filter,
    wpimath.geometry,
    wpimath.interpolation,
    wpimath.kinematics,
    wpimath.optimization,
    wpimath.path,
    wpimath.spline,
    wpimath.system,
    wpimath.system.plant,
    wpimath.trajectory,
    wpimath.trajectory.constraint,
    wpimath.units,
    wpinet,
    wpiutil,
  ]

  blocks_generator = blocks.BlocksGenerator(root_modules)

  _generatePythonUtils(blocks_generator)

  initialize_function_names = {} # Keyed by module or class name
  toolbox_function_names = {} # Keyed by module or class name
  ts_file_names = {} # Keyed by module or class name

  modules = blocks_generator.getPublicModules()
  _generateBlocksForModules(modules, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names)

  classes = blocks_generator.getPublicClasses()
  _generateBlocksForClasses(classes, blocks_generator, initialize_function_names, toolbox_function_names, ts_file_names)

  _writeInitializeFile(initialize_function_names, ts_file_names)
  _writeToolboxFile(toolbox_function_names, ts_file_names)


if __name__ == '__main__':
  app.run(main)
