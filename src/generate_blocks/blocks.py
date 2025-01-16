# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "lizlooney@google.com (Liz Looney)"

# Python Standard Library
import inspect
import json
import sys
import types
import typing

# Local modules
import python_util


_FIELD_MODULE_OR_CLASS_NAME = 'MODULE_OR_CLASS'
_FIELD_VARIABLE_NAME = 'VAR'
_FIELD_MODULE_NAME = 'MODULE'
_FIELD_CLASS_NAME = 'CLASS'
_FIELD_FUNCTION_NAME = 'FUNC'
_FIELD_ENUM_CLASS_NAME = 'ENUM_TYPE'
_FIELD_ENUM_VALUE = 'ENUM_VALUE'

_CONSTANTS_SHARED_WITH_TYPESCRIPT = {
  'FIELD_MODULE_OR_CLASS_NAME': _FIELD_MODULE_OR_CLASS_NAME,
  'FIELD_VARIABLE_NAME': _FIELD_VARIABLE_NAME,
  'FIELD_MODULE_NAME': _FIELD_MODULE_NAME,
  'FIELD_CLASS_NAME': _FIELD_CLASS_NAME,
  'FIELD_FUNCTION_NAME': _FIELD_FUNCTION_NAME,
  'FIELD_ENUM_CLASS_NAME': _FIELD_ENUM_CLASS_NAME,
  'FIELD_ENUM_VALUE': _FIELD_ENUM_VALUE,
}

_DICT_FULL_MODULE_NAME_TO_MODULE_NAME = {
  'hal._wpiHal': 'hal',
  'hal.simulation._simulation': 'hal.simulation',

  'ntcore._ntcore': 'ntcore',
  'ntcore._ntcore.meta': 'ntcore.meta',

  'wpilib._wpilib': 'wpilib',
  'wpilib._wpilib.sysid': 'wpilib.sysid',
  'wpilib.counter._counter': 'wpilib.counter',
  'wpilib.drive._drive': 'wpilib.drive',
  'wpilib.event._event': 'wpilib.event',
  'wpilib.interfaces._interfaces': 'wpilib.interfaces',
  'wpilib.shuffleboard._shuffleboard': 'wpilib.shuffleboard',
  'wpilib.simulation._simulation': 'wpilib.simulation',

  'wpimath._controls._controls.constraint': 'wpimath.trajectory.constraint',
  'wpimath._controls._controls.controller': 'wpimath.controller',
  'wpimath._controls._controls.estimator': 'wpimath.estimator',
  'wpimath._controls._controls.optimization': 'wpimath.optimization',
  'wpimath._controls._controls.path': 'wpimath.path',
  'wpimath._controls._controls.plant': 'wpimath.system.plant',
  'wpimath._controls._controls.system': 'wpimath.system',
  'wpimath._controls._controls.trajectory': 'wpimath.trajectory',
  'wpimath.filter._filter': 'wpimath.filter',
  'wpimath.geometry._geometry': 'wpimath.geometry',
  'wpimath.interpolation._interpolation': 'wpimath.interpolation',
  'wpimath.kinematics._kinematics': 'wpimath.kinematics',
  'wpimath.spline._spline': 'wpimath.spline',

  'wpinet._wpinet': 'wpinet',

  'wpiutil._wpiutil': 'wpiutil',
  'wpiutil._wpiutil.log': 'wpiutil.log',
  'wpiutil._wpiutil.sync': 'wpiutil.sync',
  'wpiutil._wpiutil.wpistruct': 'wpiutil.wpistruct',
 }


def getModuleName(m) -> str:
  if inspect.ismodule(m):
    module_name = m.__name__
  elif isinstance(m, str):
    module_name = m
  else:
    raise Exception(f'Argument m must be a module or a module name.')
  return _DICT_FULL_MODULE_NAME_TO_MODULE_NAME.get(module_name, module_name)


def getClassName(c) -> str:
  if inspect.isclass(c):
    full_class_name = python_util.getFullClassName(c)
  elif isinstance(c, str):
    full_class_name = c
  else:
    raise Exception(f'Argument c must be a class or a class name.')
  for full_module_name, module_name in _DICT_FULL_MODULE_NAME_TO_MODULE_NAME.items():
    if full_class_name.startswith(full_module_name + '.'):
      return module_name + full_class_name[len(full_module_name):]
  return full_class_name


def getSelfArgName(cls: type) -> str:
  short_class_name = cls.__name__
  return short_class_name[:1].lower() + short_class_name[1:]


def getSelfVarName(cls: type) -> str:
  return f'my{cls.__name__}'


class BlocksGenerator:
  def __init__(self, root_modules: list[types.ModuleType]):
    self._root_modules = root_modules
    (self._modules, self._classes, self._dict_class_name_to_alias) = python_util.collectModulesAndClasses(self._root_modules)
    self._dict_class_name_to_allowed_types = python_util.collectAllowedTypes(self._classes)

  def getPublicModules(self) -> list[types.ModuleType]:
    public_modules = []
    for m in self._modules:
      # TODO(lizlooney): This doesn't work for the module wpilib._wpilib.sysid.
      # For unknown reasons, there is no module named wpilib.sysid which we
      # could consider a public module.
      if '._' in python_util.getFullModuleName(m):
        continue
      public_modules.append(m)
    public_modules.sort(key=lambda m: python_util.getFullModuleName(m))
    return public_modules


  def getPublicClasses(self) -> list[type]:
    public_classes = []
    for c in self._classes:
      class_name = getClassName(c)
      if '._' in class_name:
        continue
      public_classes.append(c)
    public_classes.sort(key=lambda c: python_util.getFullClassName(c))
    return public_classes

  # Functions related to generating the blocks in the toolbox.

  def valueVariableGetter(self, var_name: str) -> str:
    return {
      'block': {
        'type': 'variables_get',
        'fields': {
          'VAR': {
            'name': var_name,
          },
        },
      },
    }

  def valueNumber(self, num_value: str) -> str:
    return {
      'shadow': {
        'type': 'math_number',
        'fields': {
          'NUM': float(num_value),
        },
      },
    }

  def valueString(self, text_value: str) -> str:
    if ((text_value.startswith('"') and text_value.endswith('"')) or
        (text_value.startswith("'") and text_value.endswith("'"))):
      text_value = text_value[1:-1]
    return {
      'shadow': {
        'type': 'text',
        'fields': {
          'TEXT': text_value,
        },
      },
    }

  def valueBoolean(self, bool_value: str) -> str:
    return {
      'shadow': {
        'type': 'logic_boolean',
        'fields': {
          'BOOL': bool_value.upper(),
        },
      },
    }

  def variableSetter(self, var_name: str, block: dict) -> str:
    return {
      'kind': 'block',
      'type': 'variables_set',
      'fields': {
        'VAR': {
          'name': var_name,
        },
      },
      'inputs': {
        'VALUE': {
          'block': block,
        },
      },
    }

  def varNameForType(self, t: str) -> str:
    while t in self._dict_class_name_to_alias:
      t = self._dict_class_name_to_alias[t]
    if t.startswith('tuple'):
      return 'myTuple'
    if t.startswith('dict'):
      return 'myDict'
    if t.startswith('list'):
      return 'myList'
    # If the type has a dot, it is an object and we should provide a variable
    # block for this type.
    lastDot = t.rfind('.')
    if lastDot != -1:
      return 'my' + t[lastDot + 1:]
    # Otherwise, we don't provide a variable block for this type.
    return ''

  def createBlock(
      self,
      block_type: str, extra_state: str,
      field_names: list[str], field_values: list[str],
      inputs: dict[str, str]) -> dict:
    block = {
      'kind': 'block',
      'type': block_type,
      'extraState': extra_state,
    }
    if field_names:
      block['fields'] = {}
      for i in range(len(field_names)):
        block['fields'][field_names[i]] = field_values[i]
    if inputs:
      block['inputs'] = inputs
    return block

  def generateVariableGetterBlock(
      self, block_type: str, var_kind: str, module_or_class_name: str,
      field_names: list[str], field_values: list[str],
      var_type: str, self_label: str, self_type: str,
      import_module: str) -> str:
    extra_state = {
      'varKind': var_kind,
      'moduleOrClassName': module_or_class_name,
      'varType': var_type,
      'importModule': import_module,
    }

    inputs = {}
    if self_label and self_type:
      extra_state['selfLabel'] = self_label
      extra_state['selfType'] = self_type
      # Check if we should plug a variable getter block into the SELF input socket.
      self_var_name = self.varNameForType(self_type)
      if self_var_name:
        inputs['SELF'] = self.valueVariableGetter(self_var_name)

    block = self.createBlock(block_type, extra_state, field_names, field_values, inputs)
    return json.dumps(block)


  def generateVariableSetterBlock(
      self, block_type: str, var_kind: str, module_or_class_name: str,
      field_names: list[str], field_values: list[str],
      var_type: str, self_label: str, self_type: str,
      import_module: str) -> str:
    extra_state = {
      'varKind': var_kind,
      'moduleOrClassName': module_or_class_name,
      'varType': var_type,
      'importModule': import_module,
    }

    inputs = {}
    # Check if we should plug a variable getter block into the VALUE input socket.
    value_var_name = self.varNameForType(var_type)
    if value_var_name:
      inputs['VALUE'] = self.valueVariableGetter(value_var_name)
    if self_label and self_type:
      extra_state['selfLabel'] = self_label
      extra_state['selfType'] = self_type
      # Check if we should plug a variable getter block into the SELF input socket.
      self_var_name = self.varNameForType(self_type)
      if self_var_name:
        inputs['SELF'] = self.valueVariableGetter(self_var_name)

    block = self.createBlock(block_type, extra_state, field_names, field_values, inputs)
    return json.dumps(block)
      
  def generateFunctionBlock(
      self, block_type: str, field_names: list[str], field_values: list[str],
      tooltip: str, return_type: str, arg_names: list[str], arg_types: list[str],
      arg_default_values: list[str], import_module: str) -> str:
    extra_state = {
      'tooltip': tooltip,
      'returnType': return_type,
      'args': [],
      'importModule': import_module,
    }

    inputs = {}
    for i in range(len(arg_names)):
      extra_state['args'].append({
        'name': arg_names[i],
        'type': arg_types[i],
      })
      # Check if we should plug a variable getter block into the argument input socket.
      var_name = self.varNameForType(arg_types[i])
      if var_name:
        inputs[f'ARG{i}'] = self.valueVariableGetter(var_name)
      elif arg_default_values[i]:
        if arg_types[i] == 'int':
          try:
            int(arg_default_values[i])
            inputs[f'ARG{i}'] = self.valueNumber(arg_default_values[i])
          except ValueError:
            print(f'WARNING - expected integer default value, found "{arg_default_values[i]}"',
                  file=sys.stderr)
        elif arg_types[i] == 'double':
          try :
            float(arg_default_values[i])
            inputs[f'ARG{i}'] = self.valueNumber(arg_default_values[i])
          except ValueError:
            print(f'WARNING - expected numeric default value, found "{arg_default_values[i]}"',
                  file=sys.stderr)
        elif arg_types[i] == 'str':
          if arg_default_values[i] == 'None':
            # TODO(lizlooney): Make a block for python None
            pass
          else:
            inputs[f'ARG{i}'] = self.valueString(arg_default_values[i])
        elif arg_types[i] == 'bool':
          if arg_default_values[i] == 'True' or arg_default_values[i] == 'False':
            inputs[f'ARG{i}'] = self.valueBoolean(arg_default_values[i])
          else:
            print(f'WARNING - expected boolean default value, found "{arg_default_values[i]}"',
                  file=sys.stderr)

    block = self.createBlock(block_type, extra_state, field_names, field_values, inputs)

    if return_type and return_type != 'None':
      var_name = self.varNameForType(return_type)
      if var_name:
        block = self.variableSetter(var_name, block)

    return json.dumps(block)

  def generateEnumValueBlock(
      self, field_names: list[str], field_values: list[str],
      enum_type: str, import_module: str) -> str:
    block_type = 'mrc_get_python_enum_value'
    extra_state = {
      'enumType': enum_type,
      'importModule': import_module,
    }
    inputs = {}
    block = self.createBlock(block_type, extra_state, field_names, field_values, inputs)
    return json.dumps(block)

  # Variable getter and setter blocks

  def generateBlocksForModuleOrClassVariables(
      self,
      module_name: str, class_name: str, var_type: str,
      getter_var_names: list[str],
      setter_var_names: list[str],
      import_lines_set: set[str],
      initialize_lines: list[str],
      toolbox_blocks: list[str]) -> str:

    # This generated code will end up in blocks/generated/<name>.ts
    import_lines_set.add('import * as getPythonVariable from "../mrc_get_python_variable";')
    if len(setter_var_names) > 0:
      import_lines_set.add('import * as setPythonVariable from "../mrc_set_python_variable";')

    block_type_getter = 'mrc_get_python_variable'
    block_type_setter = 'mrc_set_python_variable'

    # We don't have a way to get tooltips for module and class variables.
    getter_tooltips = []
    setter_tooltips = []

    if class_name:
      var_kind = 'class'
      module_or_class_name = class_name
      initialize_lines.append(
          f'getPythonVariable.initializeClassVariableGetter("{class_name}", "{var_type}", '
          f'{json.dumps(getter_var_names)}, {json.dumps(getter_tooltips)});')
      if len(setter_var_names) > 0:
        initialize_lines.append(
            f'setPythonVariable.initializeClassVariableSetter("{class_name}", "{var_type}", '
            f'{json.dumps(setter_var_names)}, {json.dumps(setter_tooltips)});')
    else:
      var_kind = 'module'
      module_or_class_name = module_name
      initialize_lines.append(
          f'getPythonVariable.initializeModuleVariableGetter("{module_name}", "{var_type}", '
          f'{json.dumps(getter_var_names)}, {json.dumps(getter_tooltips)});')
      if len(setter_var_names) > 0:
        initialize_lines.append(
            f'setPythonVariable.initializeModuleVariableSetter("{module_name}", "{var_type}", '
            f'{json.dumps(setter_var_names)}, {json.dumps(setter_tooltips)});')

    # self_label and self_type are ignored for module and class variables.
    self_label = ''
    self_type = ''
    import_module = module_name

    for var_name in getter_var_names:
      field_names = [_FIELD_MODULE_OR_CLASS_NAME, _FIELD_VARIABLE_NAME]
      if class_name:
        field_values = [class_name, var_name]
      else:
        field_values = [module_name, var_name]

      # Generate the getter block.
      toolbox_blocks.append(
          self.generateVariableGetterBlock(
              block_type_getter, var_kind, module_or_class_name,
              field_names, field_values, var_type,
              self_label, self_type, import_module))

      if var_name in setter_var_names:
        # Generate the setter block.
        toolbox_blocks.append(
            self.generateVariableSetterBlock(
                block_type_setter, var_kind, module_or_class_name,
                field_names, field_values, var_type,
                self_label, self_type, import_module))


  def generateBlocksForInstanceVariables(
      self,
      cls: type, var_type: str,
      getter_var_names: list[str],
      setter_var_names: list[str],
      members,
      import_lines_set: set[str],
      initialize_lines: list[str],
      toolbox_blocks: list[str]) -> None:

    class_name = getClassName(cls)

    # This generated code will end up in blocks/generated/<name>.ts
    import_lines_set.add('import * as getPythonVariable from "../mrc_get_python_variable";')
    if len(setter_var_names) > 0:
      import_lines_set.add('import * as setPythonVariable from "../mrc_set_python_variable";')

    block_type_getter = 'mrc_get_python_variable'
    block_type_setter = 'mrc_set_python_variable'

    getter_tooltips = []
    setter_tooltips = []
    for var_name in getter_var_names:
      tooltip = members[var_name].__doc__
      getter_tooltips.append(tooltip)
      if var_name in setter_var_names:
        setter_tooltips.append(tooltip)

    var_kind = 'instance'
    module_or_class_name = class_name

    initialize_lines.append(
        f'getPythonVariable.initializeInstanceVariableGetter("{class_name}", "{var_type}", '
        f'{json.dumps(getter_var_names)}, {json.dumps(getter_tooltips)});')
    if len(setter_var_names) > 0:
      initialize_lines.append(
          f'setPythonVariable.initializeInstanceVariableSetter("{class_name}", "{var_type}", '
          f'{json.dumps(setter_var_names)}, {json.dumps(setter_tooltips)});')

    self_label = getSelfArgName(cls)
    self_type = class_name
    import_module = ''

    for var_name in getter_var_names:
      field_names = [_FIELD_MODULE_OR_CLASS_NAME, _FIELD_VARIABLE_NAME]
      field_values = [class_name, var_name]

      # Generate the getter block.
      toolbox_blocks.append(
          self.generateVariableGetterBlock(
              block_type_getter, var_kind, module_or_class_name,
              field_names, field_values, var_type,
              self_label, self_type, import_module))

      if var_name in setter_var_names:
        # Generate the setter block.
        toolbox_blocks.append(
            self.generateVariableSetterBlock(
                block_type_setter, var_kind, module_or_class_name,
                field_names, field_values, var_type,
                self_label, self_type, import_module))


  # Function blocks

  def generateBlockForModuleFunction(
      self,
      module: types.ModuleType, key: str, function: types.FunctionType,
      toolbox_blocks: list[str]) -> None:
    module_name = getModuleName(module)
    if not function.__doc__:
      print(f'ERROR: no doc for function. {module_name}.{key}',
            file=sys.stderr)
      return

    # Make a block for each function signature. For overloaded functions, there will be more than one.
    (signatures, comments) = python_util.processFunctionDoc(function)
    if len(signatures) == 0:
      print(f'WARNING: function doc has no function signature. {module_name}.{key}',
            file=sys.stderr)
      return

    block_type = 'call_python_module_function'
    import_module = module_name

    for iSignature in range(len(signatures)):
      signature = signatures[iSignature]
      # Determine the argument names and types.
      try:
        (function_name, arg_names, arg_types, arg_default_values, return_type) = python_util.processSignature(signature)
      except:
        print(f'ERROR: signature not parseable. {module_name}.{key}',
              file=sys.stderr)
        continue
      if function_name != key:
        print(f'ERROR: signature has different function name. {module_name}.{key}',
              file=sys.stderr)
        continue

      field_names = [_FIELD_MODULE_NAME, _FIELD_FUNCTION_NAME]
      field_values = [module_name, function_name]
      tooltip = comments[iSignature]

      # Generate the function block.
      toolbox_blocks.append(
          self.generateFunctionBlock(
              block_type, field_names, field_values, tooltip, return_type,
              arg_names, arg_types, arg_default_values, import_module))


  def generateBlockForClassOrInstanceFunction(
      self,
      cls: type, member_name: str, function: types.FunctionType,
      toolbox_blocks: list[str]) -> None:
    class_name = getClassName(cls)
    self_arg_name = getSelfArgName(cls)
    full_class_name = python_util.getFullClassName(cls)
    if not function.__doc__:
      print(f'ERROR: no doc for function. {class_name}.{member_name}.',
            file=sys.stderr)
      return

    # Make a block for each function signature. For overloaded functions, there will be more than one.
    (signatures, comments) = python_util.processFunctionDoc(function)
    if len(signatures) == 0:
      print(f'WARNING: function doc has no function signature. {class_name}.{member_name}',
            file=sys.stderr)
      return

    import_module = getModuleName(cls.__module__)

    for iSignature in range(len(signatures)):
      signature = signatures[iSignature]
      # Determine the argument names and types.
      try:
        (function_name, arg_names, arg_types, arg_default_values, return_type) = python_util.processSignature(signature)
      except:
        print(f'ERROR: signature not parseable. {class_name}.{member_name}',
              file=sys.stderr)
        continue
      if function_name != member_name:
        print(f'ERROR: signature has different function name. {class_name}.{member_name}',
              file=sys.stderr)
        continue

      declaring_class_name = class_name
      inherited_function = False
      found_self_arg = False
      for i in range(len(arg_names)):
        arg_name = arg_names[i]
        arg_type = arg_types[i]
        if i == 0 and arg_name == 'self':
          found_self_arg = True
          if arg_type != full_class_name:
            inherited_function = True
            declaring_cls = python_util.getClass(arg_type)
            declaring_class_name = getClassName(declaring_cls)
            arg_names[i] = getSelfArgName(declaring_cls)
          else:
            arg_names[i] = self_arg_name
          if function_name == '__init__':
            return_type = f'{arg_type}'

      if function_name == '__init__':
        # Remove the self argument.
        arg_names.pop(0)
        arg_types.pop(0)
        arg_default_values.pop(0)
        block_type = 'call_python_constructor'
        field_names = [_FIELD_CLASS_NAME]
        field_values = [declaring_class_name]
      elif found_self_arg:
        block_type = 'call_python_instance_method'
        import_module = ''
        field_names = [_FIELD_CLASS_NAME, _FIELD_FUNCTION_NAME]
        field_values = [declaring_class_name, function_name]
      else:
        block_type = 'call_python_static_method'
        field_names = [_FIELD_CLASS_NAME, _FIELD_FUNCTION_NAME]
        field_values = [declaring_class_name, function_name]

      tooltip = comments[iSignature]

      # Generate the function block.
      toolbox_blocks.append(
          self.generateFunctionBlock(
              block_type, field_names, field_values, tooltip, return_type,
              arg_names, arg_types, arg_default_values, import_module))


  # Enum blocks

  def _createFunctionIsEnumValue(
      self, enum_cls: type) -> typing.Callable[[object], bool]:
    return lambda value: type(value) == enum_cls


  def generateBlocksForEnum(
      self,
      enum_cls: type,
      import_lines_set: set[str],
      initialize_lines: list[str],
      toolbox_blocks: list[str]) -> str:

    enum_class_name = getClassName(enum_cls)
    fnIsEnumValue = self._createFunctionIsEnumValue(enum_cls)
    enum_values = []
    enum_tooltip = ''
    for key, value in inspect.getmembers(enum_cls, fnIsEnumValue):
      enum_values.append(key)
      if not enum_tooltip:
        enum_tooltip = value.__doc__
    enum_values.sort()

    # This generated code will end up in blocks/generated/<name>.ts
    import_lines_set.add('import * as pythonEnum from "../mrc_get_python_enum_value";')
    initialize_lines.append(
        f'pythonEnum.initializeEnum("{enum_class_name}", {json.dumps(enum_values)}, {json.dumps(enum_tooltip)});')

    import_module = getModuleName(enum_cls.__module__)

    # Generate the blocks for the toolbox.
    for enum_value in enum_values:
      field_names = [_FIELD_ENUM_CLASS_NAME, _FIELD_ENUM_VALUE]
      field_values = [enum_class_name, enum_value]
      toolbox_blocks.append(
          self.generateEnumValueBlock(
              field_names, field_values, enum_class_name,
              import_module))

  def generateInitializeFunction(self, initialize_lines) -> (str, str):
    function_name = 'initialize'
    code = f'export function {function_name}() {{\n'
    for initialize_line in initialize_lines:
      code += f'  {initialize_line}\n'
    code += '}'
    return (code, function_name)

  def generateGetToolboxCategoryFunction(self, module, cls, toolbox_blocks, import_lines_set) -> (str, str):
    if cls:
      category_name = getClassName(cls)
    else:
      category_name = getModuleName(module)

    # The visible category name is just the final segment.
    lastDot = category_name.rfind('.')
    if lastDot != -1:
      visible_category_name = category_name[lastDot + 1:] 
    else:
      visible_category_name = category_name

    # This generated code will end up in blocks/generated/<name>.ts
    import_lines_set.add('import {Category} from "../../toolbox/items";')

    function_name = 'getToolboxCategory'
    code = (
        f'export function {function_name}(subcategories: Category[] = []): Category {{\n'
        '  const category: Category = {\n'
        '    kind: "category",\n'
        f'    name: "{visible_category_name}",\n'
        '    contents: [\n')
    for toolbox_block in toolbox_blocks:
      code += (
          f'      {toolbox_block},\n')
    code += (
         '    ],\n'
         '  };\n')
    code += (
         '  if (category.contents) {\n'
         '    category.contents.push(...subcategories);\n'
         '  }\n'
         '  return category;\n'
         '}')
    return (code, function_name)

  # Functions that generate TypeScript code for blocks/utils/generated/python.ts

  def generateConstants(self) -> str:
    constants = []
    for key, value in _CONSTANTS_SHARED_WITH_TYPESCRIPT.items():
      constants.append(f'export const {key} = {json.dumps(value)};')
    return '\n'.join(constants)

  def generateGetAliasFunction(self) -> str:
    code = (
        f'export function getAlias(type: string): string {{\n')

    for class_name, alias in self._dict_class_name_to_alias.items():
      code += (
          f'  if (type === {json.dumps(class_name)}) {{\n'
          f'    return {json.dumps(alias)};\n'
           '  }\n')

    code += (
        '  return "";\n'
        '}')

    return code

  def generateGetAllowedTypesFunction(self) -> str:
    code = (
        '// For the given python type, returns an array of compatible input types.\n'
        f'export function getAllowedTypes(type: string): string[] {{\n'
        '  // Subclasses\n')

    for class_name in sorted(self._dict_class_name_to_allowed_types.keys()):
      allowed_types = self._dict_class_name_to_allowed_types[class_name]
      code += (
          f'  if (type === "{class_name}") {{\n'
          f'    return {allowed_types};\n'
           '  }\n')

    code += (
        '\n'
        '  return [""];\n'
        '}')

    return code
