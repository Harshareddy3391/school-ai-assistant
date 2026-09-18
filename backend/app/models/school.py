from datetime import datetime 

from sqlalchemy import DateTime,String

from sqlalchemy.orm import Mapped,mapped_column,relationship



from app.core.database import Base 



class School(Base):
    __tablename__="school"


    id:Mapped