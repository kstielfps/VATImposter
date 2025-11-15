from django import forms


class CSVImportForm(forms.Form):
    """Formulário para importar palavras via CSV"""
    csv_file = forms.FileField(
        label='Arquivo CSV',
        required=False,
        help_text='Cada linha do CSV representa um grupo. As palavras na linha são separadas por vírgula.'
    )
    
    csv_text = forms.CharField(
        label='Ou cole o texto diretamente',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 15,
            'cols': 80,
            'placeholder': 'Frutas,Abacaxi,Manga,Banana,Laranja\nAnimais,Cachorro,Gato,Passarinho,Peixe\nComida,Pizza,Hambúrguer,Sushi,Salada'
        }),
        help_text='Cada linha representa um grupo. As palavras são separadas por vírgula. Deixe em branco se usar arquivo.'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get('csv_file')
        csv_text = cleaned_data.get('csv_text', '').strip()
        
        if not csv_file and not csv_text:
            raise forms.ValidationError('Você deve fornecer um arquivo CSV ou colar o texto diretamente.')
        
        if csv_file and csv_text:
            raise forms.ValidationError('Forneça apenas um arquivo CSV OU texto, não ambos.')
        
        if csv_file:
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError('O arquivo deve ser um CSV (.csv)')
        
        return cleaned_data

