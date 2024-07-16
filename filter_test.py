import json
from pydicom import dcmread

ds = dcmread('IM-0001-0002.dcm')

conditions = {
    'Modality': '=CT|PT',
    'SeriesDescription': '!=.*(AC for PET|CTAC).*',
    'ImageType[3]': '!=LOCALIZER',
    'SeriesNumber': '!=99'
}

f = Filter(device_name = 'PET 610', conditions = json.dumps(conditions))

assert f.validate_conditions()
assert f.match(ds)
