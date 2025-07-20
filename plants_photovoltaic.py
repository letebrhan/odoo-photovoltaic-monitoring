from odoo import models, fields, api, _, exceptions
from logging import getLogger
from datetime import datetime, timedelta
from odoo.addons.ekogrid.models.ekogrid_ticket import new_context_with_lock
import calendar
_logger = getLogger(__name__)
PHOTOVOLTAIC_DAILY_PR_MUTEX_ID = 790111
PHOTOVOLTAIC_LATEST_VALUES_MUTEX_ID = 790112
PHOTOVOLTAIC_LATEST_STRINGBOX_VALUES_MUTEX_ID = 790113

class PlantsPhotovoltaic(models.Model):
    """PlantsPhotovoltaic class definition."""
    _inherit = 'plants'
    type = fields.Selection(selection_add=[('Plant::Photovoltaic', _('Photovoltaic'))])
    single_plane = fields.Boolean(_('Single Plane'))
    power = fields.Float(compute='compute_power', string=_('Nominal Power [kWp]'), store=True, digits=(8, 2), default=0, inverse='_set_power')
    power_mwh = fields.Float(compute='compute_power', string=_('Nominal Power [MWp]'), digits=(8, 2), default=0)
    power_manual = fields.Float(_('Nominal Power manual[kWp]'))
    power_unit = fields.Char(compute='_cal_power_fields', string=_('Unit'))
    power_format = fields.Char(compute='_cal_power_fields', string=_('Format'))
    tracker = fields.Selection([('1axes', _('Single Axe')), ('2axes', _('Multi Axes'))], _('Tracker type'))
    tilt = fields.Float(_('Tilt'))
    azimuth = fields.Float(_('Azimuth'))
    installation_type = fields.Selection([('roof', 'Roof'), ('land', 'Land'), ('tracker', 'Tracker')], _('Type'))
    string_number = fields.Integer(_('Strings number'))
    panel_number = fields.Integer(_('Panels number'))
    protection_type = fields.Char(_('Interface Protection Type'), size=64)
    energy_meter = fields.Char(_('Energy Meter model'))
    creation_date = fields.Date('Creation date')
    gse_cessione_energia_convenzione = fields.Char(_('Numero convenzione SSP'), size=15)
    gse_cessione_energia_ssp_datadecorrenza = fields.Date(_('Data inizio SSP'))
    voltage = fields.Float(_('Nominal Voltage (V)'))
    voltage_type = fields.Selection([('HT', _('High')), ('MT', _('Medium')), ('BT', _('Low'))], _('Grid Voltage Type'))
    protection = fields.Selection([('integrated', _('Integrated')), ('external', _('External'))], _('Interface Protection'))
    estimated_production_pvgis_ids = fields.One2many('ekogrid.pvgis', 'plant_id', 'PVGIS')
    parent_id = fields.Many2one('plants', 'Parent Plant', domain=[('is_plane', '!=', True)])
    is_plane = fields.Boolean(_('Is a Plane?'))
    pv_sensor_plant_id = fields.Many2one('plants', 'Sensor Plant', ondelete='set null')
    subplant_ids = fields.One2many('plants', 'parent_id', _('Sub Plants'), domain=['|', ('is_plane', '=', False), ('parent_id', '=', False)])
    plane_ids = fields.One2many('plants', 'parent_id', _('Planes'), domain=[('is_plane', '=', True)])
    has_irradiance = fields.Boolean(compute='_set_has_irradiance')
    daily_production = fields.Float(compute='_get_daily_pr', digits=(20, 0), string=_('Daily Production [kWh]'), store=True)
    daily_pr = fields.Float(compute='_get_daily_pr', digits=(3, 2), string=_('Daily PR [%]'), store=True)
    daily_irradiation = fields.Float(compute='_get_daily_pr', string=_('Daily Irradiation [Wh/mq]'), store=True)
    equivalent_hours = fields.Float(compute='_get_daily_pr', digits=(4, 2), string='kWh/kWp', store=True)
    has_endana_unit = fields.Boolean(compute='_has_endana_unit')
    daily_pr_percentage = fields.Float(compute='_compute_percentage')
    pv_power_status = fields.Char(compute='_compute_latest_pv_values', help='Latest Power Status', store=True)
    pv_inv_ac_power = fields.Float(compute='_compute_latest_pv_values', group_operator='sum', help='Latest AC Power Sum[kW]', store=True)
    pv_sensor_irradiance = fields.Float(compute='_compute_latest_pv_values', group_operator='avg', help='Latest Sensor Irradiance Avg[W/mq]', store=True)
    pv_inv_ac_pr = fields.Float(compute='_compute_latest_pv_values', group_operator='avg', digits=(3, 2), help='Latest AC PR Avg[%]', store=True)
    pv_inv_ac_power_num = fields.Integer(compute='_compute_latest_pv_values', help='Latest Number of AC Power', store=True)
    pv_inv_ac_power_num_run = fields.Integer(compute='_compute_latest_pv_values', help='Latest Number of AC Power Inverter > 100 W', store=True)
    pv_inv_ac_power_num_stop = fields.Integer(compute='_compute_latest_pv_values', help='Latest Number of AC Power Inverter <= 100 W', store=True)
    pv_inv_ac_power_num_no_data = fields.Integer(compute='_compute_latest_pv_values', help='Latest Number of AC Power Inverter with out data', store=True)
    pv_stringbox_dc_curr_off = fields.Integer(compute='_compute_latest_pv_values', help='Latest Number of DC Current Stringboxes < 0.1 A', store=True)
    pv_plant_sorting_by_num = fields.Float(compute='_compute_latest_pv_values', help='Sorting PV plants based on normalized inverters(Run, stop and NC) values', store=True)
    pv_plant_sorting_by_str = fields.Char(compute='_compute_latest_pv_values', help='First Sorting PV plants based on Error grp1, then by OK/Inconsistent grp2 status', store=True)
    pv_power_status_color = fields.Char('Map Color', compute='_compute_color_map', store=True)

    def _compute_percentage(self):
        """_compute_percentage method."""
        for rec in self:
            rec.daily_pr_percentage = (rec.daily_pr if rec.daily_pr else 0) * 100

    def _auto_init(self):
        """_auto_init method."""
        result = super(PlantsPhotovoltaic, self)._auto_init()
        self.env.cr.execute("UPDATE plants SET type = 'Plant::Photovoltaic' WHERE type IS NULL")
        return result

    def plant_contacts(self):
        """plant_contacts method."""
        if self.is_plane and self.parent_id:
            return self.parent_id.notify_contact_ids + self.parent_id.follower_ids
        else:
            return self.notify_contact_ids + self.follower_ids

    @api.constrains('single_plane')
    def _constrains_single_plane(self):
        """_constrains_single_plane method."""
        if self.single_plane and len(self.plane_ids) > 0:
            raise exceptions.ValidationError(_('first delete all planes.'))

    @api.depends('name', 'task_ids', 'pv_sensor_plant_id')
    def _set_has_irradiance(self):
        """_set_has_irradiance method."""
        device_attribute = self.env['device.attributes'].search([('device_class', '=', 'Sensor'), ('device_attr', '=', 'Irradiance')])
        sensor = len(self.task_ids.filtered(lambda r: r.is_active and r.device_attribute_id and (r.device_attribute_id.id in device_attribute.ids))) > 0
        if not sensor and self.pv_sensor_plant_id and (self.pv_sensor_plant_id in self.near_plants_ids):
            self.pv_sensor_plant_id._set_has_irradiance()
            sensor = self.pv_sensor_plant_id.has_irradiance
        self.has_irradiance = sensor

    def get_power(self):
        """get_power method."""
        self.env.cr.execute('SELECT   p.id AS id,   sum(    CASE p.single_plane OR pl.is_plane IS NULL     WHEN TRUE THEN p.power_manual     ELSE pl.power_manual END    ) AS power FROM plants p   LEFT JOIN plants AS pl ON p.id = pl.parent_id WHERE p.id IN %s GROUP BY 1', (tuple(self.ids),))
        result = self.env.cr.dictfetchall()
        return result

    def compute_power(self):
        """compute_power method."""
        result = self.get_power()
        for rec in self:
            data = [x for x in result if x['id'] == rec.id]
            if data:
                rec.power = data[0]['power']
            else:
                rec.power = False
            rec.power_mwh = rec.power / 1000

    def _cal_power_fields(self):
        """_cal_power_fields method."""
        result = self.get_power()
        for record in self:
            data = [x for x in result if x['id'] == record.id]
            if data:
                record.power_unit = '%f-C'
            else:
                record.power_unit = False
            record.power_format = False

    def _set_power(self):
        """_set_power method."""
        self.power_manual = self.power
        plant = self
        while plant:
            if plant.parent_id:
                plant.parent_id.compute_power()
            plant = plant.parent_id

    @api.model
    def _get_daily_pr(self):
        """_get_daily_pr method."""
        _logger.debug('_get_daily_pr start')
        locked = False
        try:
            self.env.cr.execute('SELECT pg_try_advisory_lock(%d)' % PHOTOVOLTAIC_DAILY_PR_MUTEX_ID)
            locked = self.env.cr.fetchall()[0][0]
            if locked:
                self.env.cr.execute("\n                    UPDATE plants\n                    SET\n                        daily_production = data.daily_energy_production,\n                        daily_pr = data.daily_pr,\n                        equivalent_hours = data.equivalent_hours,\n                        daily_irradiation = data.daily_irradiation\n                    FROM (\n                        WITH logs AS (\n                            SELECT\n                                l.task_id,\n                                t.device_id,\n                                t.address_id,\n                                l.value,\n                                CASE WHEN p.is_plane AND p.parent_id IS NOT NULL THEN p.parent_id ELSE p.id END AS plant_id,\n                                t.power_peak,\n                                p.power as plant_power,\n                                da.device_attr,\n                                l.timestamp\n                            FROM public.logs l\n                                INNER JOIN tasks t ON l.task_id = t.id\n                                INNER JOIN plants p ON t.plant_id = p.id\n                                INNER JOIN device_attributes da ON t.device_attribute_id = da.id\n                            WHERE p.power > 0\n                                AND t.is_active = TRUE\n                                AND l.timestamp > date_trunc('day' :: TEXT, now())\n                                AND ((da.device_class = 'PV Production' AND da.device_attr in ('AC PR', 'AC Energy Partial'))\n                                    OR (da.device_class = 'Sensor' AND da.device_attr = 'Irradiation'))\n                        ), daily_energy_production as (\n                            SELECT\n                                l.plant_id,\n                                SUM(l.value) as energy_production,\n                                SUM(l.value)/1000/l.plant_power AS equivalent_hours\n                            FROM logs l\n                            WHERE l.device_attr = 'AC Energy Partial'\n                            GROUP BY l.plant_id, l.plant_power\n                        ), daily_irradiation as (\n                            SELECT\n                                plant_id,\n                                SUM(irradiation) as irradiation\n                            FROM (\n                                SELECT\n                                    p.id as plant_id,\n                                    l.timestamp,\n                                    AVG(l.irradiation) AS irradiation\n                                FROM plants p \n                                    INNER JOIN (\n                                        SELECT\n                                            l.plant_id,\n                                            l.task_id,\n                                            date_trunc('hour' :: TEXT, l.timestamp) AS timestamp,\n                                            SUM(l.value) AS irradiation\n                                        FROM logs l\n                                        WHERE l.device_attr = 'Irradiation'\n                                        GROUP BY 1, 2, 3\n                                    ) l ON l.plant_id IN (p.id, p.pv_sensor_plant_id)\n                                GROUP BY 1, 2\n                                ) p\n                            GROUP BY 1\n                        ), daily_pr AS (\n                            SELECT\n                              p.id as plant_id,\n                              SUM(l.pr*l.power_peak)/(p.power*1000) as pr\n                            FROM plants p\n                              INNER JOIN (\n                                          SELECT\n                                            l.plant_id,\n                                            l.power_peak,\n                                            AVG(l.value) as pr\n                                          FROM logs l\n                                          WHERE l.device_attr = 'AC PR'\n                                          GROUP BY l.plant_id, l.task_id, l.power_peak\n                                        ) l on p.id = l.plant_id\n                            GROUP BY p.id, p.power\n                        )\n                        SELECT\n                            p.id as plant_id,\n                            COALESCE(ROUND((de.energy_production/1000)::NUMERIC, 0), 0) AS daily_energy_production,\n                            COALESCE(ROUND(de.equivalent_hours::NUMERIC, 2), 0) AS equivalent_hours,\n                            COALESCE(ROUND(dpr.pr::NUMERIC, 4), 0) AS daily_pr,\n                            COALESCE(ROUND((di.irradiation)::NUMERIC, 0), 0) AS daily_irradiation\n                        FROM plants p\n                            LEFT JOIN daily_energy_production de ON de.plant_id = p.id\n                            LEFT JOIN daily_pr dpr ON dpr.plant_id = p.id\n                            LEFT JOIN daily_irradiation di ON di.plant_id = p.id\n                    ) data\n                    WHERE plants.id=plant_id\n                    ")
            else:
                _logger.debug('_get_daily_pr already running')
        finally:
            if locked:
                self.env.cr.execute('SELECT pg_advisory_unlock(%d)' % PHOTOVOLTAIC_DAILY_PR_MUTEX_ID)
        _logger.debug('_get_daily_pr end')

    @api.model
    def get_performance(self, plant_id, aggregate, ts_start, ts_end):
        """get_performance method."""
        if plant_id != False:
            plant = self.browse(plant_id)
            plant_id_with_sensor = [plant.id]
            plant_id_with_sensor += plant.subplant_ids.ids
            plant_id_with_sensor += plant.plane_ids.ids
            if plant.pv_sensor_plant_id:
                plant_id_with_sensor += [plant.pv_sensor_plant_id.id]
            plant_id_with_sensor += [plane.pv_sensor_plant_id.id for plane in plant.plane_ids if plane.pv_sensor_plant_id]
            formatted_start = ts_start if type(ts_start) == str else ts_start.strftime('%Y-%m-%d %H:%M:%S')
            formatted_end = ts_end if type(ts_end) == str else ts_end.strftime('%Y-%m-%d %H:%M:%S')
            try:
                ts_start = datetime.strptime(formatted_start, '%Y-%m-%d %H:%M:%S')
                ts_end = datetime.strptime(formatted_end, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                formatted_start = ts_start if type(ts_start) == str else ts_start.strftime('%Y-%m-%d')
                formatted_end = ts_end if type(ts_end) == str else ts_end.strftime('%Y-%m-%d')
                ts_start = datetime.strptime(formatted_start, '%Y-%m-%d')
                ts_end = datetime.strptime(formatted_end, '%Y-%m-%d')
            if aggregate == 'hour':
                ts_start = ts_start.replace(minute=0, second=0)
                ts_end = ts_end.replace(minute=59, second=59)
            elif aggregate == 'day':
                ts_start = ts_start.replace(hour=0, minute=0, second=0)
                ts_end = ts_end.replace(hour=23, minute=59, second=59)
            elif aggregate == 'month':
                ts_start = ts_start.replace(day=1, hour=0, minute=0, second=0)
                day = calendar.monthrange(ts_end.year, ts_end.month)[1]
                ts_end = ts_end.replace(day=day, hour=23, minute=59, second=59)
            elif aggregate == 'year':
                ts_start = ts_start.replace(month=1, day=1, hour=0, minute=0, second=0)
                ts_end = ts_end.replace(month=12, day=31, hour=23, minute=59, second=59)
            ts_start = ts_start.strftime('%Y-%m-%d %H:%M:%S')
            ts_end = ts_end.strftime('%Y-%m-%d %H:%M:%S')
            self.env.cr.execute("            WITH tasks_to_get AS (\n                SELECT \n                    t.id as task_id,\n                    CASE WHEN p.is_plane AND p.parent_id IS NOT NULL THEN p.parent_id ELSE p.id END AS plant_id,\n                    t.power_peak,\n                    COALESCE(p.timezone, parent_p.timezone, 'UTC') as timezone,\n                    da.device_attr\n                FROM plants p\n                    INNER JOIN tasks t ON p.id = t.plant_id\n                    INNER JOIN device_attributes da ON t.device_attribute_id = da.id\n                    LEFT JOIN plants parent_p ON p.parent_id = parent_p.id\n                WHERE p.power > 0\n                    AND t.is_active = TRUE AND p.id IN %(plant_id_with_sensor)s\n                    AND ((da.device_class = 'PV Production' AND da.device_attr in ('AC PR', 'AC Energy Partial'))\n                                    OR (da.device_class = 'Sensor' AND da.device_attr = 'Irradiation'))\n            ), logs as (\n                SELECT \n                    t.task_id,\n                    t.plant_id,\n                    t.power_peak,\n                    t.device_attr,\n                    l.timestamp AT TIME ZONE 'UTC' AT TIME ZONE t.timezone as timestamp,\n                    l.value\n                FROM tasks_to_get t \n                    INNER JOIN logs l ON t.task_id = l.task_id AND\n                        l.timestamp BETWEEN\n                            (%(ts_start)s::TIMESTAMP WITHOUT TIME ZONE AT TIME ZONE t.timezone AT TIME ZONE 'UTC') AND \n                            (%(ts_end)s::TIMESTAMP WITHOUT TIME ZONE AT TIME ZONE t.timezone AT TIME ZONE 'UTC')\n            ), energy as (\n                SELECT\n                    l.plant_id,\n                    date_trunc(%(aggregate)s :: TEXT, l.timestamp) AS timestamp,\n                    SUM(l.value) as energy_production\n                FROM logs l\n                WHERE l.plant_id = %(plant_id)s\n                    AND l.device_attr = 'AC Energy Partial'\n                GROUP BY date_trunc(%(aggregate)s :: TEXT, l.timestamp), l.plant_id\n            ), irr as (\n                SELECT\n                    plant_id,\n                    date_trunc(%(aggregate)s :: TEXT, timestamp) AS timestamp,\n                    SUM(irradiation) as irradiation\n                FROM (\n                    SELECT\n                        p.id as plant_id,\n                        l.timestamp,\n                        AVG(l.irradiation) AS irradiation\n                    FROM plants p \n                        INNER JOIN (\n                            SELECT\n                                l.plant_id,\n                                l.task_id,\n                                date_trunc('hour' :: TEXT, l.timestamp) AS timestamp,\n                                SUM(l.value) AS irradiation\n                            FROM logs l\n                            WHERE l.device_attr = 'Irradiation'\n                            GROUP BY 1, 2, 3\n                        ) l ON l.plant_id IN (p.id, p.pv_sensor_plant_id)\n                    WHERE %(plant_id)s = p.id\n                    GROUP BY 1, 2\n                    ) p\n                GROUP BY 1, 2\n            ), pr AS (\n                SELECT\n                    p.id as plant_id,\n                    l.timestamp,\n                    SUM(l.pr*l.power_peak)/(p.power*1000) as pr\n                FROM plants p\n                    INNER JOIN (\n                        SELECT\n                            l.plant_id,\n                            l.task_id,\n                            l.power_peak,\n                            date_trunc(%(aggregate)s :: TEXT, l.timestamp) AS timestamp,\n                            AVG(l.value) AS pr\n                        FROM logs l\n                        WHERE l.device_attr = 'AC PR'\n                        GROUP BY l.plant_id, l.task_id, l.power_peak, date_trunc(%(aggregate)s :: TEXT, l.timestamp)\n                        ) l on p.id = l.plant_id\n                WHERE p.id = %(plant_id)s\n                GROUP BY p.id, p.power, l.timestamp\n            )\n                SELECT\n                    period::text AS timestamp,\n                    COALESCE(ROUND((e.energy_production/1000)::NUMERIC, 2), -1) AS e_kwh,\n                    COALESCE(ROUND((irr.irradiation)::NUMERIC, 0), -1) AS irr_wh,\n                    COALESCE(ROUND(pr.pr::NUMERIC, 4), -0.01) AS pr\n                FROM plants p\n                    INNER JOIN (SELECT date_trunc(%(aggregate)s :: TEXT, generate_series) AS period FROM generate_series(\n                        %(ts_start)s::TIMESTAMP, %(ts_end)s::TIMESTAMP, ('1 ' || %(aggregate)s)::INTERVAL)) periods ON TRUE\n                    LEFT JOIN energy e ON e.plant_id = p.id AND period = e.timestamp\n                    LEFT JOIN pr ON pr.plant_id = p.id AND period = pr.timestamp\n                    LEFT JOIN irr ON irr.plant_id = p.id AND period = irr.timestamp\n                WHERE p.id = %(plant_id)s\n                ORDER BY 1;", {'plant_id_with_sensor': tuple(plant_id_with_sensor), 'plant_id': plant_id, 'aggregate': aggregate, 'ts_start': ts_start, 'ts_end': ts_end})
            res = self.env.cr.dictfetchall()
        else:
            _logger.warning('_get_performance called with no plant_id')
            res = []
        return res

    def pv_pvgis_performance_energy(self, plant_id, aggregate, start_data, end_date):
        """pv_pvgis_performance_energy method."""
        if self.id:
            plant_id = self.id
        if plant_id:
            plant = self.browse([plant_id])
            expected_data = dict(year=0)
            for e in plant.estimated_production_pvgis_ids:
                expected_data[int(e.month)] = e.avg_energy
                expected_data['year'] += e.avg_energy
            energy_data = self.get_performance(plant_id, aggregate, start_data, end_date)
            res = []
            for row in energy_data:
                timestamp = row.get('timestamp')
                dt_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                expected_value = aggregate == 'year' and expected_data['year'] or expected_data.get(dt_timestamp.month, -1)
                actual_value = round(row.get('e_kwh'), 2)
                expected_value = round(expected_value, 2)
                percent = round(actual_value * 100 / expected_value) if expected_value > 0 else 0
                res.append(dict(year=timestamp, actual_value=actual_value, expected_value=expected_value, percent=percent))
            return res

    def _has_endana_unit(self):
        """_has_endana_unit method."""
        for record in self:
            device_id = record.device_ids.search([('plant_id', '=', record.id), ('type', '=', 'Device::EndanaControlUnit')], limit=1)
            if device_id:
                record.has_endana_unit = True
            else:
                record.has_endana_unit = False

    @api.model
    def endana_iv_curve_api(self, cu_id, board_index, ru_index, socket_index, timestamp=None, next=True):
        """ Creates a JSON object with the device hierarchy

        :return: the device configuration for the plant
        """
        cu_obj = self.env['endana.control.unit'].browse(cu_id)
        iv_curve = cu_obj.iv_curve(board_index, ru_index, socket_index, timestamp, next)
        return iv_curve

    @api.model
    def endana_configuration_api(self, id):
        """ Creates a JSON object with the device hierarchy

        :return: the device configuration for the plant
        """
        cu_ids = self.env['endana.control.unit'].search([('plant_id', '=', id), ('type', '=', 'Device::EndanaControlUnit')], order='name')
        res = []
        devices = {}
        for cu in cu_ids:
            res.extend(cu.configuration())
        devices['control_units'] = res
        return devices

    def get_form_view_name_by_type(self, type):
        """get_form_view_name_by_type method."""
        if type == 'photovoltaic':
            return 'eko_plants_photovoltaic.view_plants_%s_form' % type
        return super(PlantsPhotovoltaic, self).get_form_view_name_by_type(type)

    def get_ticket_action_id(self, type):
        """get_ticket_action_id method."""
        if type == 'photovoltaic':
            return self.env.ref('eko_plants_photovoltaic.open_tickets')
        return super(PlantsPhotovoltaic, self).get_ticket_action_id(type)

    def get_activity_action_id(self, type):
        """get_activity_action_id method."""
        if type == 'photovoltaic':
            return self.env.ref('eko_plants_photovoltaic.action_activity')
        return super(PlantsPhotovoltaic, self).get_activity_action_id(type)

    @api.depends('type')
    def _compute_latest_pv_values_single_plant(self, commit=False):
        """_compute_latest_pv_values_single_plant method."""
        start_date = datetime.utcnow() - timedelta(minutes=20)
        today = start_date.strftime('%Y-%m-%d')
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        inv_ac_pow = self.get_tasks('Inverter', 'AC Power')
        sensor_irradiance = self.get_tasks('Sensor', 'Irradiance')
        inv_ac_pr = self.get_tasks('Inverter', 'AC PR')
        task_ids = inv_ac_pow + sensor_irradiance + inv_ac_pr
        if task_ids:
            select_logs = self.env['logs'].select_with_task_ids(today, today, task_ids)
            query_ac_pow = "l.device_class='Inverter' AND l.device_attr='AC Power'"
            if select_logs:
                select_logs = select_logs.decode('utf-8')
            psql_query = f"\n                            WITH logs AS ({select_logs}),\n                            latest AS (\n                                SELECT l2.*, da.device_class, da.device_attr\n                                FROM (\n                                    SELECT task_id, MAX(timestamp) AS max_timestamp\n                                    FROM logs\n                                    WHERE logs.timestamp_utc >= %(start_date)s\n                                    GROUP BY 1\n                                    ) l INNER JOIN  logs l2 ON l.task_id = l2.task_id AND l.max_timestamp = l2.timestamp\n                                    INNER JOIN device_attributes da ON l2.device_attribute_id = da.id\n                            ), plants_number_of_ac_inv AS (\n                                SELECT COALESCE(t.parent_plant_id, t.plant_id) as plant_id, COUNT(t.id) AS num_of_inverters \n                                FROM tasks t\n                                    INNER JOIN device_attributes da ON t.device_attribute_id = da.id\n                                WHERE t.is_active AND da.device_class='Inverter' AND da.device_attr='AC Power'\n                                GROUP BY 1\n                            )\n                            SELECT\n                                pv_inv.plant_id AS plant_id,\n                                pv_inv.num_of_inverters AS number_of_inverters,\n                                SUM(l.value) FILTER\n                                    (WHERE {query_ac_pow})/1000 AS ac_pow_sum_value,\n                                AVG(l.value) FILTER\n                                    (WHERE l.device_class='Sensor' AND l.device_attr='Irradiance') \n                                    As sensor_avg_value,\n                                SUM(l.value) FILTER\n                                    (WHERE l.device_class='Inverter' AND l.device_attr='AC PR' )/pv_inv.num_of_inverters \n                                    AS ac_pr_avg_value,\n                                /*BOOL_AND(l.value<100) FILTER\n                                    (WHERE l.device_class='Inverter' AND l.device_attr like 'AC Voltage%%') \n                                    AS ac_vol_status_error, */\n                                COUNT(l.value) FILTER\n                                    (WHERE {query_ac_pow} AND l.value >100) AS ac_power_num_run_value, \n                                COUNT(l.value) FILTER\n                                    (WHERE {query_ac_pow}  AND l.value <=100) AS ac_power_num_stop_value, \n                                COUNT(l.value) FILTER\n                                    (WHERE {query_ac_pow}) AS ac_power_num_with_data_value \n                            FROM plants_number_of_ac_inv pv_inv\n                                LEFT JOIN latest l ON l.plant_id = pv_inv.plant_id\n                            GROUP BY pv_inv.plant_id, pv_inv.num_of_inverters\n                            "
            self.env.cr.execute(psql_query, dict(start_date=start_date))
            result = self.env.cr.dictfetchall()
            for rec in self:
                data = [x for x in result if x['plant_id'] == rec.id]
                data = data and data[0] or None
                if data:
                    pv_inv_ac_power_num_nc = data['number_of_inverters'] > 0 and data['number_of_inverters'] - data['ac_power_num_with_data_value'] or 0
                    pow_status_com_equa = data['number_of_inverters'] == data['ac_power_num_stop_value'] + pv_inv_ac_power_num_nc
                    if data['ac_power_num_run_value'] >= 1:
                        pv_power_status = 'OK'
                    elif data['number_of_inverters'] == pv_inv_ac_power_num_nc:
                        pv_power_status = 'Inconsistent'
                    elif (data['sensor_avg_value'] is None or data['sensor_avg_value'] >= 100) and pow_status_com_equa:
                        pv_power_status = 'Error'
                    elif data['sensor_avg_value'] is not None and data['sensor_avg_value'] < 100 and pow_status_com_equa:
                        pv_power_status = 'NO_IRRADIANCE'
                    pv_plant_sorting_by_str = pv_power_status == 'Error' and 'Error group1' or 'OK/Inconsistent/NO_IRRADIANCE group2'
                    if data['ac_power_num_stop_value'] != None and data['number_of_inverters'] * rec.power > 0:
                        pv_plant_sorting_by_num = (data['ac_power_num_stop_value'] + pv_inv_ac_power_num_nc) / data['number_of_inverters'] * rec.power
                    else:
                        pv_plant_sorting_by_num = 0.0
                    if data['sensor_avg_value'] != None and data['ac_pow_sum_value'] != None and (rec.power * data['sensor_avg_value'] > 0):
                        ac_pr_value = data['ac_pow_sum_value'] / (rec.power * data['sensor_avg_value']) * 1000 * 100
                    else:
                        ac_pr_value = False
                    rec.write(dict(pv_inv_ac_power=data['ac_pow_sum_value'], pv_inv_ac_pr=ac_pr_value, pv_sensor_irradiance=data['sensor_avg_value'], pv_power_status=pv_power_status, pv_inv_ac_power_num=data['number_of_inverters'], pv_inv_ac_power_num_run=data['ac_power_num_run_value'], pv_inv_ac_power_num_stop=data['ac_power_num_stop_value'], pv_inv_ac_power_num_no_data=pv_inv_ac_power_num_nc, pv_plant_sorting_by_str=pv_plant_sorting_by_str, pv_plant_sorting_by_num=pv_plant_sorting_by_num))
                else:
                    rec.write(dict(pv_inv_ac_power=False, pv_inv_ac_pr=False, pv_sensor_irradiance=False, pv_power_status='Inconsistent', pv_inv_ac_power_num=False, pv_inv_ac_power_num_run=False, pv_inv_ac_power_num_stop=False, pv_inv_ac_power_num_no_data=False, pv_plant_sorting_by_str='OK/Inconsistent/NO_IRRADIANCE group2', pv_plant_sorting_by_num=0.0))
                rec._compute_tickets_status()
            if commit:
                self.env.cr.commit()

    @api.depends('type')
    def _compute_latest_pv_values(self, use_new_cursor=True):
        """_compute_latest_pv_values method."""
        _logger.debug('_compute_latest_pv_values start')
        with new_context_with_lock(self, use_new_cursor, PHOTOVOLTAIC_LATEST_VALUES_MUTEX_ID, 'plants_photovoltaic._compute_latest_pv_values'):
            for record in self:
                if record.type == 'Plant::Photovoltaic':
                    record._compute_latest_pv_values_single_plant(use_new_cursor)
        _logger.debug('_compute_latest_pv_values end')

    def _compute_latest_stringbox_value_single_plant(self, commit=False):
        """_compute_latest_stringbox_value_single_plant method."""
        start_date = datetime.utcnow() - timedelta(minutes=20)
        today = start_date.strftime('%Y-%m-%d')
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        stringbox_dc_curr = self.get_tasks('Stringbox', 'DC Current')
        task_ids = stringbox_dc_curr
        if task_ids:
            select_logs = self.env['logs'].select_with_task_ids(today, today, task_ids)
            if select_logs:
                select_logs = select_logs.decode('utf-8')
            psql_query = f"\n                            WITH logs AS ({select_logs}),\n                            latest AS (\n                                SELECT l2.*, da.device_class, da.device_attr\n                                FROM (\n                                    SELECT task_id, MAX(timestamp) AS max_timestamp\n                                    FROM logs\n                                    WHERE logs.timestamp_utc >= %(start_date)s\n                                    GROUP BY 1\n                                    ) l INNER JOIN  logs l2 ON l.task_id = l2.task_id AND l.max_timestamp = l2.timestamp\n                                    INNER JOIN device_attributes da ON l2.device_attribute_id = da.id\n                                )\n                            SELECT\n                                l.plant_id AS plant_id,                                 \n                                COUNT(l.value) FILTER \n                                    (WHERE l.device_class='Stringbox' AND l.device_attr='DC Current' and l.value < 0.1) \n                                    AS dc_curr_count_value \n                            FROM latest l\n                            GROUP BY l.plant_id\n                            "
            self.env.cr.execute(psql_query, dict(start_date=start_date))
            result = self.env.cr.dictfetchall()
            for rec in self:
                data = [x for x in result if x['plant_id'] == rec.id]
                data = data and data[0] or None
                if data:
                    rec.write(dict(pv_stringbox_dc_curr_off=data['dc_curr_count_value']))
                else:
                    rec.write(dict(pv_stringbox_dc_curr_off=False))
            if commit:
                self.env.cr.commit()

    @api.depends('name')
    def _compute_latest_stringbox_values(self, use_new_cursor=True):
        """_compute_latest_stringbox_values method."""
        _logger.debug('_compute_latest_stringbox_values start')
        with new_context_with_lock(self, use_new_cursor, PHOTOVOLTAIC_LATEST_STRINGBOX_VALUES_MUTEX_ID, 'plants_photovoltaic._compute_latest_stringbox_values_single_plant'):
            for record in self:
                record._compute_latest_stringbox_value_single_plant(use_new_cursor)
        _logger.debug('_compute_latest_stringbox_values end')

    def pv_performance_image(self, pv_start_month, pv_end_month):
        """pv_performance_image method."""
        css_files = ['/eko_plants_photovoltaic/static/src/css/paramgraph.css']
        jsx_files = ['/ekogrid/static/src/js/highstock_support_functions.js', '/ekogrid/static/src/jsx/HighchartsReact.jsx', '/eko_plants_photovoltaic/static/src/jsx/PerformaceGraph.jsx']
        data = {'name': 'pv_performance_image', 'callbacks': {'getPerformanceData': {'model_name': self._name, 'function_name': 'get_performance', 'is_model': True}}, 'component_name': 'PerformaceGraph', 'default_props': {'res_id': self.id, 'aggregation': 'month', 'context': {}, 'start_date': pv_start_month, 'end_date': pv_end_month, 'showMenu': False, 'energyOnly': self.show_energy_only(), 'is_resized': True}, 'css_files': css_files, 'jsx_files': jsx_files}
        return self.env['eko.react.export'].export_base64(data)

    def show_energy_only(self):
        """show_energy_only method."""
        return False

    def pv_performance_data(self, pv_start_month, pv_end_month):
        """pv_performance_data method."""
        self.ensure_one()
        data = self.get_performance(self.id, 'month', pv_start_month, pv_end_month)
        for d in data:
            if d['e_kwh'] < 0:
                d['e_kwh'] = 0
            if d['irr_wh'] < 0:
                d['irr_wh'] = 0
        return data

    def pv_tickets_list(self, pv_start_month, pv_end_month):
        """pv_tickets_list method."""
        self.ensure_one()
        tickets = self.env['ekogrid.ticket'].search([('client_notified', '=', True), ('plant_id', '=', self.id), ('date', '>=', pv_start_month), ('date', '<=', pv_end_month)])
        return tickets

    def pv_pvgis_full_performance(self):
        """pv_pvgis_full_performance method."""
        creation_date = ''
        start_month = ''
        if self.creation_date:
            creation_date = datetime.strptime(self.creation_date.strftime('%Y-%m-%d'), '%Y-%m-%d')
            start_month = datetime.strptime(self.creation_date.strftime('%Y-%m-%d'), '%Y-%m-%d').month
        else:
            _logger.warning('No creation date found')
            return []
        end_month = datetime.today().month
        first_pvgis = self.estimated_production_pvgis_ids.filtered(lambda r: int(r.month) >= start_month)
        last_pvgis = self.estimated_production_pvgis_ids.filtered(lambda r: int(r.month) <= end_month)
        first_year_avg_energy = sum(first_pvgis.mapped('avg_energy'))
        year_expected_value = sum(self.estimated_production_pvgis_ids.mapped('avg_energy'))
        last_year_expected_value = sum(last_pvgis.mapped('avg_energy'))
        depriciation_percent = 0.75
        value_factor = year_expected_value * depriciation_percent / 100
        performance_data = self.get_performance(self.id, 'year', creation_date.strftime('%Y-%m-%d %H:%M:%S'), datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
        res = []
        count, size = (1, len(performance_data))
        for row in performance_data:
            if count == 1:
                expected_value = first_year_avg_energy
            elif size == count:
                expected_value = last_year_expected_value - value_factor
            else:
                expected_value = year_expected_value - value_factor
                year_expected_value = expected_value
            count += 1
            actual_value = round(row.get('e_kwh'), 2)
            expected_value = round(expected_value, 2)
            percent = round(actual_value * 100 / expected_value) if expected_value > 0 else 0
            res.append(dict(year=row.get('timestamp'), actual_value=actual_value, expected_value=expected_value, percent=percent))
        return res

    def pv_pvgis_full_performance_chart_config(self):
        """pv_pvgis_full_performance_chart_config method."""
        data = self.pv_pvgis_full_performance()
        series_data = [[], []]
        year = []
        for row in data:
            series_data[0].append([row['year'], row['actual_value']])
            series_data[1].append([row['year'], row['expected_value']])
            year.append(datetime.strptime(row['year'], '%Y-%m-%d %H:%M:%S').year)
        series = [{'type': 'column', 'name': 'Actual Value', 'data': series_data[0]}, {'type': 'column', 'name': 'Expected Value', 'data': series_data[1]}]
        return {'chart': {'type': 'chart'}, 'title': {'text': 'Produzione reale/stimata annuale'}, 'credits': {'enabled': False}, 'rangeSelector': {'enabled': False}, 'xAxis': {'type': 'category', 'categories': year, 'crosshair': True}, 'yAxis': {'min': 0, 'title': {'text': 'Energy (kWh)'}}, 'series': series}

    def pv_pvgis_full_performance_image(self, *kwargs):
        """pv_pvgis_full_performance_image method."""
        jsx_files = ['/ekogrid/static/src/js/highstock_support_functions.js', '/ekogrid/static/src/jsx/HighchartsReact.jsx', '/ekogrid/static/src/jsx/DrawChart.jsx']
        css_files = ['/ekogrid/static/src/css/draw_chart.css']
        data = {'name': 'pv_pvgis_full_performance_image', 'callbacks': {'get_chart_data': {'model_name': self._name, 'function_name': 'pv_pvgis_full_performance_chart_config', 'is_model': False}}, 'component_name': 'DrawChart', 'default_props': {'res_id': self.id, 'context': {}, 'showMenu': False, 'is_resized': True}, 'jsx_files': jsx_files, 'css_files': css_files}
        return self.env['eko.react.export'].export_base64(data)

    def map_plant_type_form_view(self):
        """
        Function to return the dictionary of for view for the plant type.
        """
        res = super(PlantsPhotovoltaic, self).map_plant_type_form_view()
        if self.type == 'Plant::Photovoltaic':
            res = {'Plants': 'eko_plants_photovoltaic.view_plants_photovoltaic_form', 'Administration': 'eko_plants_photovoltaic.view_plants_form_photovoltaic_administration', 'Technical Data': 'eko_plants_photovoltaic.view_plants_form_photovoltaic_technical', 'Reports': 'eko_plants_photovoltaic.view_plants_form_photovoltaic_reports', 'Settings': 'eko_plants_photovoltaic.view_plants_form_photovoltaic_config', 'Monitoring': 'eko_plants_photovoltaic.view_plants_form_photovoltaic_monitoring'}
        return res

    def create_virtual_datalogger_buses_single(self):
        """create_virtual_datalogger_buses_single method."""
        super(PlantsPhotovoltaic, self).create_virtual_datalogger_buses_single()
        if self.type == 'Plant::Photovoltaic':
            data_logger_id = self.get_virtual_datalogger()
            self.create_virtual_bus_single(data_logger_id, 'Photovoltaic', 'photovoltaic')

    def pv_draft_configuration(self):
        """pv_draft_configuration method."""
        for record in self:
            if record.type == 'Plant::Photovoltaic':
                record.create_virtual_datalogger_buses()
                bus_id = record.get_virtual_bus('photovoltaic')
                device_model_id = self.env.ref('eko_plants_photovoltaic.device_models_pv_device_model')
                device_name = 'sensor'
                device_id = self.env['devices'].search([('address', '=', device_name), ('bus_id', '=', bus_id.id)])
                if not device_id:
                    device_id = self.env['devices'].create(dict(name=device_name, address=device_name, bus_id=bus_id.id, device_model_id=device_model_id.id, plant_id=record.id))
                create_tasks = self.env['create.tasks'].create(dict(device_id=device_id.id))
                addresses = create_tasks.with_context(active_id=device_id.id).default_get('device_id')['address_ids']
                addresses = self.env['addresses'].browse(addresses[0][2])
                create_tasks.address_ids = addresses
                create_tasks.create_tasks()

    @api.depends('pv_power_status')
    def _compute_color_map(self):
        """_compute_color_map method."""
        color_map = {'OK': 'green', 'Error': 'red', 'Inconsistent': 'orange', 'NO_IRRADIANCE': 'blue'}
        for power_status in self:
            power_status.pv_power_status_color = color_map.get(power_status.pv_power_status, '')

    def get_metric_info(self):
        """get_metric_info method."""
        if self.type == 'Plant::Photovoltaic':
            return dict(metric_name='peak_power', metric_value=self.power, metric_unit='kWp')
        return super(PlantsPhotovoltaic, self).get_metric_info()

    def pv_define_meter_inverter_config_fn(self):
        """pv_define_meter_inverter_config_fn method."""
        config = self.env['eko.meter.inverter.config'].create({'plant_id': self.id})
        config.pv_create_meter_inverter_table()
        return {'type': 'ir.actions.act_window', 'res_model': 'eko.meter.inverter.config', 'res_id': config.id, 'view_mode': 'form', 'target': 'new'}