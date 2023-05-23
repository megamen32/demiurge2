import peewee

class Prompt(peewee.Model):
    id= peewee.AutoField(primary_key=True)
    text= peewee.CharField(unique=True)
    class Meta:
        database=peewee.SqliteDatabase('promt.db')

