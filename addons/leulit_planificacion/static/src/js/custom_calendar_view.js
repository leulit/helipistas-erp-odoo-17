/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { onWillStart } from "@odoo/owl";

patch(AttendeeCalendarModel.prototype, {
    
    async updateAttendeeData(data) {
        const attendeeFilters = data.filterSections.partner_ids;
        let isEveryoneFilterActive = true;
        let attendeeIds = [];
        const eventIds = Object.keys(data.records).map(id => Number.parseInt(id));
        if (attendeeFilters) {
            const allFilter = attendeeFilters.filters.find(filter => filter.type === "all")
            isEveryoneFilterActive = allFilter && allFilter.active || false;
            attendeeIds = attendeeFilters.filters.filter(filter => filter.type !== "all" && filter.value).map(filter => filter.value);
        }
        data.attendees = await this.orm.call(
            "res.partner",
            "get_attendee_detail",
            [attendeeIds, eventIds],
        );
        const currentPartnerId = this.user.partnerId;
        if (!isEveryoneFilterActive) {
            const activeAttendeeIds = new Set(attendeeFilters.filters
                .filter(filter => filter.type !== "all" && filter.value && filter.active)
                .map(filter => filter.value)
            );
            // Duplicate records per attendee
            const newRecords = {};
            let duplicatedRecordIdx = -1;
            for (const event of Object.values(data.records)) {
                const eventData = event.rawRecord;
                const attendees = eventData.partner_ids && eventData.partner_ids.length ? eventData.partner_ids : [eventData.partner_id[0]];
                let duplicatedRecords = 0;
                for (const attendee of attendees) {
                    if (!activeAttendeeIds.has(attendee)) {
                        continue;
                    }
                    // Records will share the same rawRecord.
                    const record = { ...event };
                    const attendeeInfo = data.attendees.find(a => (
                        a.id === attendee &&
                        a.event_id === event.id
                    ));
                    record.attendeeId = attendee;
                    // Colors are linked to the partner_id but in this case we want it linked
                    // to attendeeId
                    record.colorIndex = attendee;
                    if (attendeeInfo) {
                        record.attendeeStatus = attendeeInfo.status;
                        record.isAlone = attendeeInfo.is_alone;
                        record.isCurrentPartner = attendeeInfo.id === currentPartnerId;
                        record.calendarAttendeeId = attendeeInfo.attendee_id;
                    }
                    const recordId = duplicatedRecords ? duplicatedRecordIdx-- : record.id;
                    // Index in the records
                    record._recordId = recordId;
                    newRecords[recordId] = record;
                    duplicatedRecords++;
                }
            }
            data.records = newRecords;
        } else {
            for (const event of Object.values(data.records)) {
                const eventData = event.rawRecord;
                event.attendeeId = eventData.partner_id && eventData.partner_id[0]
                const attendeeInfo = data.attendees.find(a => (
                    a.id === currentPartnerId &&
                    a.event_id === event.id
                ));
                if (attendeeInfo) {
                    event.isAlone = attendeeInfo.is_alone;
                    event.calendarAttendeeId = attendeeInfo.attendee_id;
                }
            }
        }
    }

});