from django import forms


class CSVImportForm(forms.Form):
    """Formulário para importar palavras via CSV"""
    csv_file = forms.FileField(
        label='Arquivo CSV',
        help_text='Cada linha do CSV representa um grupo. As palavras na linha são separadas por vírgula ou ponto-e-vírgula.'
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('O arquivo deve ser um CSV (.csv)')
        return csv_file

