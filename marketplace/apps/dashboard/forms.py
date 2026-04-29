from django import forms

from apps.products.models import Brand, Category, Product


class DashboardProductForm(forms.ModelForm):
    main_image = forms.ImageField(required=False)

    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'brand',
            'description',
            'short_description',
            'price',
            'old_price',
            'stock',
            'sku',
            'weight',
            'is_active',
            'is_featured',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('parent__name', 'name')
        self.fields['brand'].queryset = Brand.objects.order_by('name')

        text_classes = 'w-full px-4 py-3 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-yellow-400 bg-white'
        checkbox_classes = 'w-4 h-4 rounded accent-yellow-400'
        for name, field in self.fields.items():
            if name in {'is_active', 'is_featured'}:
                field.widget.attrs.update({'class': checkbox_classes})
            elif name == 'main_image':
                field.widget.attrs.update({
                    'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100'
                })
            else:
                field.widget.attrs.update({'class': text_classes})
