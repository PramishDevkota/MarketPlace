from django.db import models
# import uuid

# # Create your models here.


# class BaseModel(models.Model):
    

#     uid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
#     created_at = models.DateField(auto_now_add=True)
#     updated_at = models.DateField(auto_now=True)


    
#     class Meta:     
#         abstract = True   # as a base class , treats, it will create as a class
#         ordering = ["-created_at"]

# class Product(BaseModel):

#     product_name = models.CharField(max_length=100)
#     product_slug = models.SlugField(unique=True)
#     product_description  = models.TextField()
#     price = models.PositiveIntegerField(default=0)
#     discount_price = models.PositiveIntegerField(blank=True,null=True)
#     quantity = models.CharField(max_length= 100, null =True, blank=True)
#     STATUS_CHOICES = (("draft", "Draft"),("published", "Published"),("sold", "Sold"),)
#     status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="draft")
#     is_available = models.BooleanField(default=True)


#     def __str__(self):
#         return self.product_name

# class ProductMetaInformation(BaseModel):

    
#     product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="meta")  
#     product_measuring = models.CharField(max_length=100, null = True, blank=True, choices = (("KG", "Kilogram"),("G", "Gram"),("ML", "Milliliter"),("L", "Liter"),))
#     product_quantity = models.CharField(max_length=100, null=True, blank=True)
#     is_restrict = models.BooleanField(default=False)
#     restrict_quantity = models.PositiveIntegerField(blank=True, null=True)

#     def __str__(self):
#         return self.product.product_name

# class ProductImage(BaseModel):

#     product_images = models.ImageField(upload_to="products/images")
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")


#     def __str__(self):
#         return f"Image of {self.product.product_name}"





class Produc(models.Model):

    product_name = models.CharField(max_length=100)
    price = models.FloatField()
    product_description  = models.TextField()
    stock = models.IntegerField(default=1)
    status = models.BooleanField(default=0)


    discount_price = models.PositiveIntegerField(blank=True,null=True)
    quantity = models.CharField(max_length= 100, null =True, blank=True)

