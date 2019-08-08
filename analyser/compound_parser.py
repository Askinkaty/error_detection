import re

class CompoundParser():
    def __init__(self, lang):
        self.lang = lang
        self.parse_compound = MAP_LANGUAGE_TO_COMPOUND_PARSER[lang]


def parse_compound_finnish(potential_compound):
    ''' Not used for FINNISH, only as placeholder for others'''
    all_morph_data = []
    is_compound = False
    stems_analysis = potential_compound.split('#')
    if len(stems_analysis) > 1:
        is_compound = True
    for stem_analysis in stems_analysis:
        morph_data = stem_analysis.split('+')
        all_morph_data.append(morph_data)
    return all_morph_data, is_compound

    
def parse_compound_erzya(potential_compound):
    #print ("*** INPUT POTENTIAL_COMPOUND %s" % potential_compound)
    all_morph_data = []
    is_compound = False
    stems_analysis = potential_compound.split('HYPH-COMBO.ACRO@')
    if len(stems_analysis) == 1:
        stems_analysis = stems_analysis[0].split('@+SerialVerb+Cmp')
        #print(stems_analysis)
    if len(stems_analysis) > 1:
        is_compound = True
    for stem_analysis in stems_analysis:
        morph_data = stem_analysis.split('+')
        all_morph_data.append(morph_data)
    #print(all_morph_data)
    return all_morph_data, is_compound


def parse_compound_swedish(potential_compound):
    #print ("*** INPUT POTENTIAL_COMPOUND %s" %potential_compound)
    all_morph_data = []
    is_compound = False
    potential_compound = potential_compound.replace('<CAP>', '')
    potential_compound = potential_compound.replace('<SUFF>', '')
    stems_analysis = re.findall(r'\w+(?:<\+*\w*\/*\w+>)*', potential_compound)
    #print('STEMS ANALYSIS: %s' % stems_analysis)
    if len(stems_analysis) > 1:
        is_compound = True
    for stem_analysis in stems_analysis:
        morph_data = []
        base_part = re.findall(r'(\w+)<', stem_analysis)
        if len(base_part) == 0:
            base_part.append(stem_analysis) 
        #print('Base part: {0}'.format(base_part))
        tags_data = re.findall(r'<(\+*\w+)>', stem_analysis)
        #print('TAGS DATA: %s' % tags_data)
        if len(base_part) != 0:
            morph_data.append(base_part[0]) 
        for tag_data in tags_data:
            morph_data.append(tag_data)
        all_morph_data.append(morph_data)
    return all_morph_data, is_compound


def parse_compound_kazakh(potential_compound):
    #print ("*** INPUT POTENTIAL_COMPOUND %s" %potential_compound)
    all_morph_data = []
    is_compound = False
    stems_analysis = re.findall(r'\w+(?:<\+*\w*\/*\w+>)*', potential_compound)
    #print('STEMS ANALYSIS: %s' % stems_analysis)
    ### TEMPORARY HACK: we do not take bases except for the first one returned by an analyzer
    stems_analysis = [stems_analysis[0]]
    #print('STEMS ANALYSIS 0: %s' % stems_analysis[0])
    for stem_analysis in stems_analysis:
        morph_data = []
        base_part = re.findall(r'(\w+)<', stem_analysis)
        if len(base_part) == 0:
            base_part.append(stem_analysis) 
        #print('Base part: {0}'.format(base_part))
        tags_data = re.findall(r'<(\+*\w+)>', stem_analysis)
        #print('TAGS DATA: %s' % tags_data)
        if len(base_part) != 0:
            morph_data.append(base_part[0]) 
        for tag_data in tags_data:
            morph_data.append(tag_data)
        all_morph_data.append(morph_data)
    #print(all_morph_data)
    return all_morph_data, is_compound

    
MAP_LANGUAGE_TO_COMPOUND_PARSER = {
    'Russian':     None,
    'Finnish':     parse_compound_finnish,
    'Erzya':       parse_compound_erzya, ## ??? TODO
    'Meadow-Mari': parse_compound_finnish, ## ??? TODO
    'North-Saami': parse_compound_finnish, ## ??? TODO
    'Swedish':     parse_compound_swedish,
    'German':      parse_compound_swedish, ## morphisto, self.german_POS_map
    'Komi-Zyrian': parse_compound_finnish, ## giella  ## ??? TODO
    'Komi-Permiak': parse_compound_finnish, ## giella  ## ??? TODO
    'Udmurt':      parse_compound_finnish, # giella
    'Sakha':       parse_compound_swedish,
    'Kazakh':      parse_compound_kazakh ## apertium kaz
    }
