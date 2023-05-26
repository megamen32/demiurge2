import peewee

class Prompt(peewee.Model):
    id= peewee.AutoField(primary_key=True)
    text= peewee.CharField(unique=True)
    class Meta:
        database=peewee.SqliteDatabase('promt.db')

class ImageMidjourney(peewee.Model):
    id= peewee.AutoField(primary_key=True)
    url= peewee.CharField(unique=True)
    prompt=peewee.CharField()
    def filename(self):
        return   self.url.split('/')[-1]
    class Meta:
        database=peewee.SqliteDatabase('promt.db')