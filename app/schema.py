from pydantic import BaseModel, Field, model_validator
import datetime 
from typing import Literal 

class Meta(BaseModel):
    user_id: str = Field(min_length=1, description= "User identification")
    date: datetime.date = Field(description= "Calender date")
    total_meetings: int = Field(ge=0, le=24, description = "Total meetings attended that day")
    meeting_hours_per_day: float = Field(ge=0.0, le=16.0, description = "Total hour spent in meetings")
    average_gap_between_meetings_minutes: float = Field(ge=0.0, le=720.0, description = "Average free minutes between meetings")
    messages_sent_after_8pm: int = Field(ge=0, le=300, description= "After hours signal ")
    context_switches_per_hour: int = Field(ge=0, le=20, description = "Average number of app switches per hour")


    @model_validator(mode = "after")
    def meeting_and_hours(self):
        if self.total_meetings == 0 and self.meeting_hours_per_day > 0:
            raise ValueError(
                "meeting hour per day most be 0 when total meetings is 0"
            )
        
        if self.meeting_hours_per_day == 0 and self.total_meetings > 0 :
            raise ValueError(
                "if there is meeting happening then there will be some total meeting hours also"
            )
        
        if self.total_meetings <= 1 and self.average_gap_between_meetings_minutes > 0:
            raise ValueError(
                "average gap between meetings minutes require at least 2 meetings"
            )
        
        if self.total_meetings > 0:
            avg_duration = self.meeting_hours_per_day / self.total_meetings
            if avg_duration < 0.2:
                raise ValueError(
                    "Average meeting duration is too low unrealistic"
                )
            if avg_duration > 4:
                raise ValueError(
                    "Average meeting duration is too long unrealistic"
                )

        if self.meeting_hours_per_day > self.total_meetings*4:
            raise ValueError(
                "Meeting hours are inconsistent"
            )
        
        if self.date > datetime.date.today():
            raise ValueError("date cannot be in the future")
        
        return self


class LableMeta(Meta):
    label: Literal["FOCUS", "NEUTRAL", "BURNOUT"] 