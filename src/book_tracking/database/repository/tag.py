from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.book_tracking.database.models import Tag
from src.book_tracking.database.repository.base import BaseRepository
from src.book_tracking.database.schemas import TagRead
from src.book_tracking.database.schemas.tag import TagDetailRead


class TagRepository(BaseRepository[Tag, TagRead]):
    model = Tag
    schema = TagRead


    def _options(self) -> list:
        return [
            # selectinload(Tag.book_associations),
        ]
    
    async def get_by_id_detail(self, id: int) -> Optional[TagDetailRead]:
        stmt = (
            select(self.model)
            .where(self.model.id == id)
            .options(selectinload(Tag.book_associations))
        )
        result = await self.session.execute(stmt)
        instance = result.scalars().one_or_none()
        
        if instance:
            return TagDetailRead.model_validate(instance)
        return None

    async def get_all_detail(self) -> list[TagDetailRead]:
        stmt = (
            select(self.model)
            .options(selectinload(Tag.book_associations))
        )
        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        
        return [TagDetailRead.model_validate(obj) for obj in instances]
