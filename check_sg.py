import PySimpleGUI as sg
print('version:', getattr(sg, '__version__', getattr(sg, 'version', 'unknown')))
print('has_theme:', hasattr(sg, 'theme'))
print('has_theme_set:', hasattr(sg, 'theme_set'))
print('has_theme_previewer:', hasattr(sg, 'theme_previewer'))
print('available_theme_attrs:', [n for n in dir(sg) if 'theme' in n.lower()])
