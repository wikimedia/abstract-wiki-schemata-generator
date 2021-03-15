import contextlib
import enum
import io
import logging
import os
import re
import yaml


class _FormatEnum(enum.Enum):
    NORMAL = 0
    CANONICAL = 1


_BUILTIN_TYPES = {
    _FormatEnum.NORMAL: {
        'Z1': {
            'Z1K1': 'Z4',
        },
        'Z2': {
            'Z1K1': 'special',
            'Z2K1': 'Z6',
            'Z2K2': 'Z1',
            'Z2K3': 'Z12',
        },
        'Z3': {
            'Z1K1': 'special',
            'Z3K1': 'Z4',
            'Z3K2': 'Z6',
            'Z3K3': 'Z12',
        },
        'Z4': {
            'Z1K1': 'special',
            'Z4K1': 'Z4',
            'Z4K2': 'Z10',
            'Z4K3': 'Z8',
        },
        'Z5': {
            'Z1K1': 'special',
            'Z5K1': 'Z50',
            'Z5K2': 'Z1',
        },
        'Z6': {
            'literally': {
                'required': ['Z1K1', 'Z6K1'],
                'properties': {
                    'Z1K1': {
                        'type': 'string',
                        'enum': ['Z6'],
                    },
                    'Z6K1': {
                        'type': 'string',
                    },
                },
                'additionalProperties': False,
            }
        },
        'Z7': {
            'Z1K1': 'special',
            'Z7K1': 'Z4',
            'patternProperties': {
                # TODO: Fill in this regex.
                'regex': 'Z1',
            },
        },
        'Z8': {
            'Z1K1': 'special',
            'Z8K1': 'Z10',
            'Z8K2': 'Z4',
            'Z8K3': 'Z10',
            'Z8K4': 'Z10',
            'Z8K5': 'Z8',
            'notRequired': { 'Z8K4' },
        },
        'Z9': {
            'literally': {
                'required': ['Z1K1', 'Z9K1'],
                'properties': {
                    'Z1K1': {
                        'type': 'string',
                        'enum': ['Z9'],
                    },
                    'Z9K1': {
                        'type': 'string',
                        # TODO: Fill in this regex.
                        'pattern': 'regex',
                    },
                },
                'additionalProperties': False,
            }
        },
        'Z10': {
            'references': {
                'Z10_empty': {
                    'Z1K1': 'special',
                },
                'Z10_full': {
                    'Z1K1': 'special',
                    'Z10K1': 'Z1',
                    'Z10K2': 'Z10',
                },
            }
        },
        'Z11': {
            'Z1K1': 'special',
            'Z11K1': 'Z60',
            'Z11K2': 'Z6',
        },
        'Z12': {
            'Z1K1': 'special',
            'Z12K1': 'Z10',
        },
        'Z14': {
            'Z1K1': 'special',
            'Z14K1': 'Z8',
            'Z14K2': 'Z7',
            'Z14K3': 'Z16',
            'Z14K4': 'Z6',
        },
        'Z16': {
            'Z1K1': 'special',
            'Z16K1': 'Z61',
            'Z16K2': 'Z6',
        },
        'Z17': {
            'Z1K1': 'special',
            'Z17K1': 'Z4',
            'Z17K2': 'Z6',
            'Z17K3': 'Z12',
        },
        'Z18': {
            'Z1K1': 'special',
            'Z18K1': 'Z6',
        },
        'Z20': {
            'Z1K1': 'special',
            'Z20K1': 'Z7',
            'Z20K2': 'Z8',
        },
        'Z21': {
            'Z1K1': 'special',
        },
        'Z22': {
            'Z1K1': 'special',
            'Z22K1': 'Z1',
            'Z22K2': 'Z1',
        },
        'Z23': {
            'Z1K1': 'special',
        },
        'Z39': {
            'Z1K1': 'special',
            'Z39K1': 'Z6',
        },
        'Z40': {
            'Z1K1': 'special',
            'Z40K1': 'Z50',
        },
        'Z50': {
            'Z1K1': 'special',
            'Z50K1': 'Z10',
        },
        'Z60': {
            'Z1K1': 'special',
            'Z60K1': 'Z6',
        },
        'Z61': {
            'Z1K1': 'special',
            'Z61K1': 'Z6',
        },
        'Z80': {
            'Z1K1': 'special',
            'Z80K1': 'Z6',
        },
        'Z86': {
            'Z1K1': 'special',
            'Z86K1': 'Z6',
        },
        'Z99': {
            'Z1K1': 'special',
            'Z99K1': 'Z1',
        },
    },
}


_RECORD_PATTERN = re.compile(r'^Z[1-9]\d*(K[1-9]\d*)?$')


@contextlib.contextmanager
def _printable():
    fake_file = io.StringIO()
    yield fake_file
    fake_file.seek(0)
    print(fake_file.read())



class SchemaComponent:

    _DEFINITIONS_PATH = ['definitions', 'objects']

    def __init__(self, form='NORMAL'):
        form = getattr(_FormatEnum, form)
        self._builtin_dict = _BUILTIN_TYPES[form]
        self._to_update = []

    def _id_for(self, ZID):
        return f'{self._tag}/{ZID}'

    def _reference_for(self, ZID):
        return '/'.join(['#'] + self._DEFINITIONS_PATH + [ZID])
    
    def _ref_dict(self, value):
        return {'$ref': value}

    def _external_reference(self, ZID):
        return f'{self._id_for(ZID)}{self._reference_for(ZID)}'

    def _special_z1k1(self, zid):
        return {
            'type': 'object',
            'required': ['Z1K1', 'Z9K1'],
            'properties': {
                'Z1K1': {
                    'type': 'string',
                    'enum': ['Z9'],
                },
                'Z9K1': {
                    'type': 'string',
                    'enum': [zid],
                },
            },
            'additionalProperties': False,
        }

    def _update_from_spec(self, object_dict, zid, display_zid, spec):
        # TODO: Exit early if this is already populated.
        zid_dict = object_dict.setdefault(zid, {})

        # Case 1: spec embeds references to other ZIDs.
        references = spec.get('references')
        if references is not None:
            oneofs = []
            for key, value in references.items():
                self._to_update.append((key, display_zid, value))
                oneofs.append(self._ref_dict(self._reference_for(key)))
            zid_dict['oneOf'] = oneofs
            return

        literally = spec.get('literally')
        if literally is not None:
            assert(len(spec) == 1)
            zid_dict.update(literally)
            return

        # Do the thing.
        # Populate properties.
        properties_dict = zid_dict.setdefault('properties', {})
        required = set()
        for key, value in spec.items():
            if not _RECORD_PATTERN.match(key):
                continue
            if _RECORD_PATTERN.match(value):
                properties_dict[key] = self._ref_dict(self._external_reference(value))
            elif key == 'Z1K1' and value == 'special':
                allof = properties_dict.setdefault(key, {}).setdefault('allOf', [])
                allof.append(self._ref_dict(self._reference_for('Z9')))
                allof.append(self._special_z1k1(display_zid))
            else:
                logging.debug(f'Unrecognized property spec: {{{key}: {value}}}')
                raise Exception
            required.add(key)

        # Process non-required properties (we require properties by default).
        required = required - set(spec.get('notRequired', {}))
        zid_dict['required'] = sorted(list(required))

        # Process pattern properties.
        pattern_properties = spec.get('patternProperties')
        if pattern_properties is not None:
            if len(pattern_properties) != 1:
                logging.debug(f'pattern_dict should contain one key: {pattern_properties}')
                raise Exception
            for regex, reference in pattern_properties.items():
                pattern_dict = zid_dict.setdefault('patternProperties', {})
                pattern_dict[regex] = self._ref_dict(self._external_reference(reference))
                break

        # Process additionalProperties (prohibited by default).
        allow_additional = False
        if spec.get('additionalProperties'):
            # TODO: This can be a reference, too.
            allow_additional = True
        zid_dict['additionalProperties'] = allow_additional

    def generate(self, root_directory, tag, ZID, dry_run=True):
        self._root = root_directory
        self._tag = tag

        schema = {}

        # Generate ID and reference to base object.
        schema['$id'] = self._id_for(ZID)
        schema.update(self._ref_dict(self._reference_for(ZID)))

        # Create definitions dict.
        object_dict = schema
        for key in self._DEFINITIONS_PATH:
            object_dict = object_dict.setdefault(key, {})

        literal_spec = self._builtin_dict.get(ZID)
        literal_name = f'{ZID}_literal'
        self._to_update.append((literal_name, ZID, literal_spec))

        # Any ZObject can be either a literal, a function call literal (Z7),
        # or a reference (Z9).
        object_dict[ZID] = {
            'oneOf': [
                self._ref_dict(elem) for elem in [
                    self._external_reference('Z7'),
                    self._external_reference('Z9'),
                    self._reference_for(literal_name),
                ]
            ]
        }

        while self._to_update:
            zid, display_zid, spec = self._to_update.pop()
            self._update_from_spec(object_dict, zid, display_zid, spec)

        with contextlib.ExitStack() as stack:
            if dry_run:
                outp = stack.enter_context(_printable())
            else:
                outp = open(os.path.join(self._root, f'{ZID}.yaml'), 'w')
            yaml.dump(schema, outp)

    def list(self):
        for key in self._builtin_dict.keys():
            print(key)


if __name__ == '__main__':
    import fire
    logging.basicConfig(level=logging.DEBUG)
    fire.Fire(SchemaComponent)         
