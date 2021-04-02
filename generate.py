import contextlib
import enum
import io
import logging
import os
import re
import sys
import yaml


class _FormatEnum(enum.Enum):
    NORMAL = 0
    CANONICAL = 1


def _Z10_specialization(ZID):
    return f'Z10_of_{ZID}'


def _Z8_of(input_ZID, output_ZID):
    return {
        'literally': {
            'allOf': [
                {'external': 'Z8'},
                {
                    'type': 'object',
                }
            ],
        },
    }


def _Z9_of(ZID):
    """Convenience function for creating specialized Z9 types."""
    return {
        'literally': {
            'allOf': [
                {'external': 'Z9'},
                {
                    'type': 'object',
                    'properties': {
                        'Z9K1': {
                            'type': 'string',
                            'enum': [ZID],
                        },
                    },
                },
            ],
        },
    }


def _Z10_of(ZID):
    """Convenience function for creating specialized Z10 types."""
    return {
        'literally': {
            'allOf': [
                {'external': 'Z10'},
                {
                    'oneOf': [
                        {'external': 'Z10_empty', 'id': 'Z10'},
                        {
                            'type': 'object',
                            'properties': {
                                'Z10K1': { 'external': ZID },
                                'Z10K2': { 'internal': _Z10_specialization(ZID) },
                            },
                            'required': [ 'Z10K1', 'Z10K2' ],
                        },
                    ],
                },
            ],
        },
    }


_BUILTIN_TYPES = {
    _FormatEnum.NORMAL: {
        'Z1': {
            'comment': 'Z1/Object (Z4/Type)',
            'references': {
                'Z1_terminal': {
                    'literally': {
                        'oneOf': [
                            {'external': 'Z6'},
                            {'external': 'Z9'},
                        ],
                    },
                },
                'Z1_nonterminal': {
                    'patternProperties': {
                        '^Z[1-9]\d*(K[1-9]\d*)?$': {
                            'internal': 'Z1_generic',
                        },
                    },
                },
                'Z1_generic': {
                    'literally': {
                        'oneOf': [
                            {'internal': 'Z1_terminal'},
                            {'internal': 'Z1_nonterminal'},
                        ],
                    },
                },
                'Z1_nongeneric': {
                    'Z1K1': {'external': 'Z4'},
                },
            },
            'literally': {
                'oneOf': [
                    {'internal': 'Z1_generic'},
                    {'internal': 'Z1_nongeneric'},
                ],
            },
        },
        'Z2': {
            'comment': 'Z2/Persistent object (Z4/Type)',
            'Z1K1': 'special',
            'Z2K1': {'external': 'Z6'},
            'Z2K2': {'external': 'Z1'},
            'Z2K3': {'external': 'Z12'},
        },
        'Z3': {
            'comment': 'Z3/Key (Z4/Type)',
            'Z1K1': 'special',
            'Z3K1': {'external': 'Z4'},
            'Z3K2': {'external': 'Z6'},
            'Z3K3': {'external': 'Z12'},
        },
        'Z4': {
            'comment': 'Z4/Type (Z4/Type)',
            'references': {
                _Z10_specialization('Z3'): _Z10_of('Z3'),
            },
            'Z1K1': 'special',
            'Z4K1': {'internal': 'Z4'},
            'Z4K2': {'internal': _Z10_specialization('Z3')},
            'Z4K3': {'external': 'Z8'},
        },
        'Z5': {
            'comment': 'Z5/Error (Z4/Type)',
            'Z1K1': 'special',
            'Z5K1': {'external': 'Z50'},
            'Z5K2': {'external': 'Z1'},
        },
        'Z6': {
            'comment': 'Z6/String (Z4/Type)',
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
                'type': 'object',
                'additionalProperties': False,
            }
        },
        'Z7': {
            'comment': 'Z7/Function call (Z4/Type)',
            'Z1K1': 'special',
            'Z7K1': {'external': 'Z4'},
            'patternProperties': {
                # TODO: Use $data to infer from Z8's declarations.
                '^Z[1-9]\d*(K[1-9]\d*)?$': {'external': 'Z1'},
            },
        },
        'Z8': {
            'comment': 'Z8/Function (Z4/Type)',
            'references': {
                _Z10_specialization('Z17'): _Z10_of('Z17'),
                _Z10_specialization('Z20'): _Z10_of('Z20'),
                _Z10_specialization('Z14'): _Z10_of('Z14'),
            },
            'Z1K1': 'special',
            'Z8K1': {'internal': _Z10_specialization('Z17')},
            'Z8K2': {'external': 'Z4'},
            'Z8K3': {'internal': _Z10_specialization('Z20')},
            'Z8K4': {'internal': _Z10_specialization('Z14')},
            'Z8K5': {'internal': 'Z8'},
            'notRequired': { 'Z8K4' },
        },
        'Z9': {
            'comment': 'Z9/Reference (Z4/Type)',
            'literally': {
                'required': ['Z1K1', 'Z9K1'],
                'properties': {
                    'Z1K1': {
                        'type': 'string',
                        'enum': ['Z9'],
                    },
                    'Z9K1': {
                        'type': 'string',
                        'pattern': '^Z[1-9]\d*(K[1-9]\d*)?$',
                    },
                },
                'additionalProperties': False,
                'type': 'object',
            },
        },
        'Z10': {
            'comment': 'Z10/List (Z4/Type)',
            'references': {
                'Z10_empty': {
                    'Z1K1': 'special',
                },
                'Z10_full': {
                    'Z1K1': 'special',
                    'Z10K1': {'external': 'Z1'},
                    'Z10K2': {'internal': 'Z10'},
                },
            },
            'literally': {
                'oneOf': [
                    {'internal': 'Z10_empty'},
                    {'internal': 'Z10_full'},
                ],
            },
        },
        'Z11': {
            'comment': 'Z11/Monolingual text (Z4/Type)',
            'Z1K1': 'special',
            'Z11K1': {'external': 'Z60'},
            'Z11K2': {'external': 'Z6'},
        },
        'Z12': {
            'comment': 'Z12/Multilingual text (Z4/Type)',
            'references': {
                _Z10_specialization('Z11'): _Z10_of('Z11'),
            },
            'Z1K1': 'special',
            'Z12K1': {'internal': _Z10_specialization('Z11')},
        },
        'Z14': {
            'comment': 'Z14/Implementation (Z4/Type)',
            'Z1K1': 'special',
            'Z14K1': {'external': 'Z8'},
            'Z14K2': {'external': 'Z7'},
            'Z14K3': {'external': 'Z16'},
            'Z14K4': {'external': 'Z6'},
        },
        'Z16': {
            'comment': 'Z16/Code (Z4/Type)',
            'Z1K1': 'special',
            'Z16K1': {'external': 'Z61'},
            'Z16K2': {'external': 'Z6'},
        },
        'Z17': {
            'comment': 'Z17/Argument declaration (Z4/Type)',
            'Z1K1': 'special',
            'Z17K1': {'external': 'Z4'},
            'Z17K2': {'external': 'Z6'},
            'Z17K3': {'external': 'Z12'},
        },
        'Z18': {
            'comment': 'Z18/Argument reference (Z4/Type)',
            'Z1K1': 'special',
            'Z18K1': {'external': 'Z6'},
        },
        'Z20': {
            'comment': 'Z20/Tester (Z4/Type)',
            'Z1K1': 'special',
            'Z20K1': {'external': 'Z7'},
            'Z20K2': {'external': 'Z8'},
        },
        'Z21': {
            'comment': 'Z21/Unit (Z4/Type)',
            'Z1K1': 'special',
        },
        'Z22': {
            'comment': 'Z22/Pair (Z4/Type)',
            'Z1K1': 'special',
            'Z22K1': {'external': 'Z1'},
            'Z22K2': {'external': 'Z1'},
        },
        'Z23': {
            'comment': 'Z23/Nothing (Z4/Type)',
            'Z1K1': 'special',
        },
        'Z39': {
            'comment': 'Z39/Key reference (Z4/Type)',
            'Z1K1': 'special',
            'Z39K1': {'external': 'Z6'},
            'Z39K2': {'external': 'Z1'},
            'notRequired': {'Z39K2'},
        },
        # Overwritten by the below. Why is this like this?
        'Z40': {
            'Z1K1': 'special',
            'Z40K1': {'external': 'Z50'},
        },
        'Z40': {
            'comment': 'Z40/Boolean (Z4/Type)',
            'references': {
                'Z9_for_Z40': {
                    'literally': {
                        'allOf': [
                            {'external': 'Z9'},
                            {
                                'type': 'object',
                                'properties': {
                                    'Z9K1': {
                                        'type': 'string',
                                        'enum': ['Z41', 'Z42'],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            'Z1K1': {'internal': 'special'},
            'Z40K1': {'internal': 'Z40'},
        },
        'Z50': {
            'comment': 'Z50/Error type (Z4/Type)',
            'references': {
                _Z10_specialization('Z3'): _Z10_of('Z3'),
            },
            'Z1K1': 'special',
            'Z50K1': {'internal': _Z10_specialization('Z3')},
        },
        'Z60': {
            'comment': 'Z60/Language (Z4/Type)',
            'Z1K1': 'special',
            'Z60K1': {'external': 'Z6'},
        },
        'Z61': {
            'comment': 'Z61/Programming language (Z4/Type)',
            'Z1K1': 'special',
            'Z61K1': {'external': 'Z6'},
        },
        'Z80': {
            'comment': 'Z80/Byte (Z4/Type)',
            'Z1K1': 'special',
            'Z1K1': 'special',
            'Z80K1': {'external': 'Z6'},
        },
        'Z86': {
            'comment': 'Z86/Character (Z4/Type)',
            'references': {
                'Z6_length_1': {
                    'literally': {
                        'allOf': [
                            {'external': 'Z6'},
                            {
                                'type': 'object',
                                'properties': {
                                    'Z6K1': {
                                        'type': 'string',
                                        'pattern': '^.$',
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            'Z1K1': 'special',
            'Z86K1': {'internal': 'Z6_length_1'},
        },
        'Z99': {
            'comment': 'Z99/Quote (Z4/Type)',
            'Z1K1': 'special',
            'Z99K1': {'external': 'Z1'},
        },
    },
}


_RECORD_PATTERN = re.compile(r'^Z[1-9]\d*(K[1-9]\d*)?$')


class SchemaComponent:

    _DEFINITIONS_PATH = ['definitions', 'objects']

    def __init__(self, form='NORMAL'):
        form = getattr(_FormatEnum, form)
        self._builtin_dict = _BUILTIN_TYPES[form]
        self._to_update = []

    def _id_for(self, ZID):
        if self._tag is None:
            return ZID
        return f'{self._tag}_{ZID}'

    def _reference_for(self, ZID):
        return '/'.join(['#'] + self._DEFINITIONS_PATH + [ZID])
    
    def _ref_dict(self, value):
        return {'$ref': value}

    def _external_reference(self, ZID, external_id=None):
        if external_id is None:
            external_id = ZID
        return f'{self._id_for(external_id)}{self._reference_for(ZID)}'

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

    def _replace_references(self, spec):
        result = {}
        for key, value in spec.items():
            if isinstance(value, dict):
                internal = value.get('internal')
                if internal is not None:
                    result[key] = self._ref_dict(self._reference_for(internal))
                    continue

                external = value.get('external')
                if external is not None:
                    args = [external]
                    extern_id = value.get('id')
                    if extern_id is not None:
                        args.append(extern_id)
                    result[key] = self._ref_dict(self._external_reference(*args))
                    continue

                result[key] = self._replace_references(value)
            elif isinstance(value, list):
                new_list = []
                for element in value:
                    # TODO: Fix this kludge.
                    augmented = {'element': element}
                    replaced = self._replace_references(augmented)
                    new_list.append(replaced['element'])
                result[key] = new_list
            else:
                result[key] = value
        return result

    def _update_from_spec(self, object_dict, zid, display_zid, spec):
        # TODO: Exit early if this is already populated.
        zid_dict = object_dict.setdefault(zid, {})

        # Step 1: create internal references.
        references = spec.get('references')
        if references is not None:
            for key, value in references.items():
                self._to_update.append((key, display_zid, value))

        # Step 2: if spec has "literally," processing should stop after.
        literally = spec.get('literally')
        if literally is not None:
            zid_dict.update(literally)
            return

        # Step 3: populate properties.
        properties_dict = {}
        required = set()
        for key, value in spec.items():
            if not _RECORD_PATTERN.match(key):
                continue
            if '$ref' in value:
                properties_dict[key] = value
                continue
            if key == 'Z1K1' and value == 'special':
                allof = properties_dict.setdefault(key, {}).setdefault('allOf', [])
                allof.append(self._ref_dict(self._external_reference('Z9')))
                allof.append(self._special_z1k1(display_zid))
                continue
            logging.debug(f'Unrecognized property spec: {{{key}: {value}}}')
            raise Exception

        if properties_dict:
            zid_dict['properties'] = properties_dict

        # Step 4: non-required properties (we require properties by default).
        required = set(properties_dict.keys()) - set(spec.get('notRequired', {}))
        if required:
            zid_dict['required'] = sorted(list(required))

        # Step 5: process pattern properties.
        pattern_properties = spec.get('patternProperties')
        if pattern_properties is not None:
            zid_dict['patternProperties'] = pattern_properties

        # Step 6: process additionalProperties (prohibited by default).
        allow_additional = False
        if spec.get('additionalProperties'):
            # TODO: This can be a reference, too.
            allow_additional = True
        zid_dict['additionalProperties'] = allow_additional

        # Step 7: most things are objects.
        zid_dict['type'] = 'object'

    def generate(self, ZID, root_directory=None, tag=None, dry_run=True):
        if root_directory is None:
            assert(dry_run == True)
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
        literal_spec = self._replace_references(literal_spec)
        literal_name = f'{ZID}_literal'
        self._to_update.append((literal_name, ZID, literal_spec))

        # Any ZObject can be either a literal, a function call literal (Z7),
        # or a reference (Z9).
        # This causes crazy circular reference shit.
        _ = """
        object_dict[ZID] = {
            'oneOf': [
                self._ref_dict(elem) for elem in [
                    self._external_reference('Z7'),
                    self._external_reference('Z9'),
                    self._reference_for(literal_name),
                ]
            ]
        }
        """
        object_dict[ZID] = self._ref_dict(self._reference_for(literal_name))

        while self._to_update:
            zid, display_zid, spec = self._to_update.pop()
            self._update_from_spec(object_dict, zid, display_zid, spec)

        # Compose the resulting .yaml file.
        #
        # Start with comment if appropriate.
        contents = ''
        comment = literal_spec.get('comment')
        if comment is not None:
            contents += f'# {comment}\n'

        # Append YAML dict.
        fake_file = io.StringIO()
        yaml.dump(schema, fake_file)
        fake_file.seek(0)
        contents += fake_file.read()

        with contextlib.ExitStack() as stack:
            if dry_run:
                outp = sys.stdout
            else:
                outp = stack.enter_context(open(os.path.join(self._root, f'{ZID}.yaml'), 'w'))
            outp.write(contents)

    def list(self):
        for key in self._builtin_dict.keys():
            print(key)


if __name__ == '__main__':
    import fire
    logging.basicConfig(level=logging.DEBUG)
    fire.Fire(SchemaComponent)         
