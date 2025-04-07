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
import pathlib
import re
import types

# absl
from absl import app
from absl import flags
from absl import logging

# robotpy
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

# Local modules
import python_util


FLAGS = flags.FLAGS

flags.DEFINE_string('output_directory', None, 'The directory where output should be written.')


class Examine:

  def __init__(self, root_modules: list[types.ModuleType]):
    self._root_modules = root_modules
    (self._packages, self._modules, self._classes, self._dict_class_name_to_alias) = python_util.collectModulesAndClasses(self._root_modules)
    self._dict_class_name_to_subclass_names = python_util.collectSubclasses(self._classes)
    self.output_file = open(f"{FLAGS.output_directory}/examine/examine.txt", "w", encoding="utf-8")
    self.show_ids = False


  def close(self):
    self.output_file.close()
    

  def _isModuleFunction(self, parent, key: str, some_object) -> bool:
    return (
        inspect.ismodule(parent) and
        inspect.isroutine(some_object) and
        inspect.isbuiltin(some_object))


  def _isStaticMethod(self, parent, key: str, some_object) -> bool:
    return (
        inspect.isclass(parent) and
        inspect.isroutine(some_object) and
        inspect.isbuiltin(some_object))


  def _isInstanceMethod(self, parent, key: str, some_object) -> bool:
    return (
        inspect.isclass(parent) and
        inspect.isroutine(some_object) and
        inspect.ismethoddescriptor(some_object) and
        some_object.__name__ != "__init__")


  def _examine(self,
      indent: str, full_name: str,
      parent, key: str, some_object,
      ids: list[int], classes_from_function_signatures: list[type]) -> None:
    details = []
    if python_util.isEnum(some_object):
      details.append("blockEnum")
    if self._isModuleFunction(parent, key, some_object):
      details.append("blockModuleFunction")
    if self._isStaticMethod(parent, key, some_object):
      details.append("blockStaticMethod")
    if python_util.isConstructor(parent, key, some_object):
      details.append("blockConstructor")
    if self._isInstanceMethod(parent, key, some_object):
      details.append("blockInstanceMethod")
    if python_util.isModuleVariableReadable(parent, key, some_object):
      details.append("blockModuleVariableGetter")
    if python_util.isModuleVariableWritable(parent, key, some_object):
      details.append("blockModuleVariableSetter")
    if python_util.isClassVariableReadable(parent, key, some_object):
      details.append("blockClassVariableGetter")
    if python_util.isClassVariableWritable(parent, key, some_object):
      details.append("blockClassVariableSetter")
    if python_util.isInstanceVariableReadable(parent, key, some_object):
      details.append("blockInstanceVariableGetter")
    if python_util.isInstanceVariableWritable(parent, key, some_object):
      details.append("blockInstanceVariableSetter")

    if python_util.isTypeAlias(parent, key, some_object):
      details.append("isTypeAlias")
    if python_util.isOverloaded(some_object):
      details.append("isOverloaded")

    if inspect.ismodule(some_object):
      full_name = python_util.getFullModuleName(some_object)
      details.append("ismodule")
    if inspect.isclass(some_object):
      details.append("isclass")
      if not python_util.isTypeAlias(parent, key, some_object):
        full_name = python_util.getFullClassName(some_object)
    if hasattr(some_object, '__package__'):
      details.append(f"__package__='{some_object.__package__}'")
    #if hasattr(some_object, '__all__'):
    #  details.append("__all__")
    if inspect.isfunction(some_object):
      details.append("isfunction")
    if inspect.isgeneratorfunction(some_object):
      details.append("isgeneratorfunction")
    if inspect.isgenerator(some_object):
      details.append("isgenerator")
    if inspect.iscoroutinefunction(some_object):
      details.append("iscoroutinefunction")
    if inspect.iscoroutine(some_object):
      details.append("iscoroutine")
    if inspect.isawaitable(some_object):
      details.append("isawaitable")
    if inspect.isasyncgenfunction(some_object):
      details.append("isasyncgenfunction")
    if inspect.isasyncgen(some_object):
      details.append("isasyncgen")
    if inspect.istraceback(some_object):
      details.append("istraceback")
    if inspect.isframe(some_object):
      details.append("isframe")
    if inspect.iscode(some_object):
      details.append("iscode")
    if inspect.isbuiltin(some_object):
      details.append("isbuiltin")
    if inspect.ismethodwrapper(some_object):
      details.append("ismethodwrapper")
    if inspect.isroutine(some_object):
      details.append("isroutine")
    if inspect.isabstract(some_object):
      details.append("isabstract")
    if inspect.ismethoddescriptor(some_object):
      details.append("ismethoddescriptor")
    if inspect.isdatadescriptor(some_object):
      details.append("isdatadescriptor")
    if inspect.isgetsetdescriptor(some_object):
      details.append("isgetsetdescriptor")
    if inspect.ismemberdescriptor(some_object):
      details.append("ismemberdescriptor")

    if isinstance(some_object, bool):
      details.append("bool")
    elif isinstance(some_object, int):
      details.append("int")
    if isinstance(some_object, float):
      details.append("float")
    if isinstance(some_object, str):
      details.append("str")
    if isinstance(some_object, list):
      details.append("list")
    if isinstance(some_object, dict):
      details.append("dict")
    if isinstance(some_object, tuple):
      details.append("tuple")

    if inspect.ismodule(some_object):
      details.append(f"{python_util.getFullModuleName(some_object)} {some_object}")
    elif inspect.isclass(some_object):
      details.append(f"{python_util.getFullClassName(some_object)}")
    else:
      details.append(f"type={type(some_object)}")
    if hasattr(some_object, "__name__") and some_object.__name__ and not inspect.ismodule(some_object) and not inspect.isclass(some_object):
      details.append(f"__name__='{some_object.__name__}'")
    if hasattr(some_object, "__module__") and some_object.__module__ and not inspect.isclass(some_object):
      details.append(f"__module__='{some_object.__module__}'")

    if some_object.__doc__:
      doc = re.sub(r"object at 0x[0-9a-fA-F]{9}", "object at 0x123456789", some_object.__doc__)
      joined = "\\n".join(doc.split("\n"))
      details.append(f"__doc__='{joined}'")

    if self.show_ids:
      print(f"{indent}> {full_name}: {id(some_object)} {' '.join(details)}", file=self.output_file)
    else:
      print(f"{indent}> {full_name}: {' '.join(details)}", file=self.output_file)

    if id(some_object) in ids:
      return
    ids.append(id(some_object))

    if inspect.isroutine(some_object) and some_object.__doc__:
      signature_line = some_object.__doc__.split("\n")[0]
      for cls in python_util.getClassesFromSignatureLine(signature_line):
        if python_util.isBuiltInClass(cls):
          continue
        if cls not in classes_from_function_signatures:
          classes_from_function_signatures.append(cls)

    if inspect.ismodule(some_object) and python_util.isBuiltInModule(some_object):
      return
    if inspect.isclass(some_object) and python_util.isBuiltInClass(some_object):
      return
    if python_util.isEnum(parent):
      return

    force_show_everything = False

    if inspect.ismodule(some_object) or inspect.isclass(some_object) or inspect.isdatadescriptor(some_object):
      indent += "  "
      for key in sorted(dir(some_object)):
        if key == "_":
          if not force_show_everything:
            continue
        if inspect.isdatadescriptor(some_object):
          if key != "fget" and key != "fset":
            continue
        member = getattr(some_object, key)
        if python_util.ignoreMember(some_object, key, member):
            continue
        self._examine(
            indent, f"{full_name}.{key}",
            some_object, key, member,
            ids, classes_from_function_signatures)


  def examine(self) -> None:
    ids = []
    classes_from_function_signatures = []
    for module in self._root_modules:
      self._examine(
          "", python_util.getFullModuleName(module),
          None, python_util.getFullModuleName(module), module,
          ids, classes_from_function_signatures)
    while len(classes_from_function_signatures):
      classes = classes_from_function_signatures
      classes.sort(key=lambda c: python_util.getFullClassName(c))
      break_out = True
      for cls in classes:
        if id(cls) not in ids:
          self._examine(
              "", "",
              None, "", cls,
              ids, classes_from_function_signatures)
          break_out = False
      if break_out:
        break


  def showPackagesAndModulesAndClasses(self) -> None:
    print("\n\nPackages:", file=self.output_file)
    print("\n".join(sorted(self._packages)), file=self.output_file)
    print("\n\nModules:", file=self.output_file)
    print("\n".join(sorted([python_util.getFullModuleName(module) for module in self._modules])), file=self.output_file)
    print("\n\nClasses:", file=self.output_file)
    print("\n".join(sorted([python_util.getFullClassName(cls) for cls in self._classes])), file=self.output_file)
    print("\n\nType Aliases:", file=self.output_file)
    print("\n".join(sorted([f"{key}: {value}" for (key, value) in self._dict_class_name_to_alias.items()])), file=self.output_file)
    print("\n\nSubclasses:", file=self.output_file)
    print("\n".join(sorted([f"{key}: {value}" for (key, value) in self._dict_class_name_to_subclass_names.items()])), file=self.output_file)


def main(argv):
  del argv  # Unused.

  if not FLAGS.output_directory:
    logging.error(f"You must specify the --output_directory argument")
    return

  pathlib.Path(f"{FLAGS.output_directory}/examine").mkdir(exist_ok=True)

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

  examine = Examine(root_modules)
  examine.examine()
  examine.showPackagesAndModulesAndClasses()
  examine.close()


if __name__ == "__main__":
  app.run(main)
