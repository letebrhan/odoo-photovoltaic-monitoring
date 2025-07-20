from odoo import models, fields, api, _, exceptions
from logging import getLogger
import os
_logger = getLogger(__name__)

class PlantsPhotovoltaic(models.Model):
    """PlantsPhotovoltaic class definition."""
    _inherit = 'plants'

    def pv_create_default_charts_data_loggers(self, base_domain, base_chart_attributes):
        """pv_create_default_charts_data_loggers method."""
        self.ensure_one()
        EkogridChart = self.env['ekogrid.chart']
        dl_lost = self.get_tasks('Datalogger', 'Lost')
        dl_nologs = self.get_tasks('Datalogger', 'No Logs')
        if dl_lost or dl_nologs:
            domain = base_domain + [('title', '=', 'DataLogger Lost'), ('subtitle', '=', 'DataLogger'), ('task_ids', 'in', (dl_lost + dl_nologs).ids)]
            base_chart_attributes.update(dict(title='DataLogger Lost', subtitle='DataLogger', type='highstock', time_frame='7', aggregate='10 minute'))
            chart_id_dl_lost = EkogridChart.search(domain)
            if not chart_id_dl_lost:
                chart_id_dl_lost = EkogridChart.create(base_chart_attributes)
                [chart_id_dl_lost.add_serie_with_tasks_default([task.id]) for task in dl_lost + dl_nologs]

    def pv_create_default_charts_pv_production(self, base_domain, base_chart_attributes):
        """pv_create_default_charts_pv_production method."""
        self.ensure_one()
        EkogridChart = self.env['ekogrid.chart']
        energy_meter = self.get_tasks('PV Production', 'AC Energy Partial')
        pv_power = self.get_tasks('PV Production', 'AC Power')
        sensor_irradiation = self.get_tasks('Sensor', 'Irradiation')
        title = ['Daily generation', 'Monthly generation']
        subtitle = 'PV Production'
        base_domain_pv = base_domain + [('subtitle', '=', subtitle)]
        base_chart_attributes.update(dict(subtitle=subtitle, type='highstock', compute_deviation=False))
        for t in title:
            if t == 'Daily generation':
                aggregate = 'day'
                time_frame = '31'
                name = 'Generated energy'
            if t == 'Monthly generation':
                aggregate = 'month'
                time_frame = '365'
                name = 'Generated energy'
            if energy_meter:
                domain = base_domain_pv + [('title', '=', t), ('task_ids', 'in', energy_meter.ids)]
                base_chart_attributes.update(dict(title=t, time_frame=time_frame, aggregate=aggregate, stacking_type=False))
                chart_id_meter = EkogridChart.search(domain)
                if not chart_id_meter:
                    chart_id_meter = EkogridChart.create(base_chart_attributes)
                    chart_id_meter.add_serie_with_tasks_default(task_ids=energy_meter.ids, type='column', name=name, function='sum', function_many='sum')
        ' # create generation of the day charts'
        if energy_meter or pv_power:
            domain_gen_day = base_domain_pv + [('title', '=', 'Generation of the day'), ('task_ids', 'in', (pv_power + energy_meter).ids)]
            base_chart_attributes.update(dict(title='Generation of the day', time_frame='today', aggregate='hour', stacking_type=False))
            chart_id_gen_day = EkogridChart.search(domain_gen_day)
            if not chart_id_gen_day:
                chart_id_gen_day = EkogridChart.create(base_chart_attributes)
                chart_id_gen_day.add_serie_with_tasks_default(task_ids=energy_meter.ids, type='column', name='Active energy', function='sum', function_many='sum')
                chart_id_gen_day.add_serie_with_tasks_default(task_ids=pv_power.ids, name='Active power')
        ' # create Energy Meter charts'
        if energy_meter or sensor_irradiation:
            domain_meter = base_domain_pv + [('title', '=', 'AC Energy'), ('task_ids', 'in', (energy_meter + sensor_irradiation).ids)]
            base_chart_attributes.update(dict(title='AC Energy', time_frame='today', aggregate='hour', stacking_type='normal'))
            chart_id_energy_meter = EkogridChart.search(domain_meter)
            if not chart_id_energy_meter:
                chart_id_energy_meter = EkogridChart.create(base_chart_attributes)
                if energy_meter:
                    [chart_id_energy_meter.add_serie_with_tasks_default([task.id], group='a', type='column', function='avg', function_many='sum') for task in energy_meter]
                if sensor_irradiation:
                    [chart_id_energy_meter.add_serie_with_tasks_default([task.id], group='b', function='avg', function_many='sum') for task in sensor_irradiation]

    def pv_create_default_charts_sensor(self, base_domain, base_chart_attributes):
        """pv_create_default_charts_sensor method."""
        self.ensure_one()
        EkogridChart = self.env['ekogrid.chart']
        ' #create External conditions charts'
        sensor_mod_temp = self.get_tasks('Sensor', 'Module Temperature')
        sensor_amb_temp = self.get_tasks('Sensor', 'Ambient Temperature')
        sensor_irradiance = self.get_tasks('Sensor', 'Irradiance')
        sensor_irradiation = self.get_tasks('Sensor', 'Irradiation')
        sensor_ext_temp = sensor_mod_temp + sensor_amb_temp + sensor_irradiance + sensor_irradiation
        if sensor_ext_temp:
            domain = base_domain + [('title', '=', 'External conditions'), ('subtitle', '=', 'Sensor'), ('task_ids', 'in', sensor_ext_temp.ids)]
            base_chart_attributes.update(dict(title='External conditions', subtitle='Sensor', type='highstock', aggregate='10 minute', time_frame='7', compute_deviation=False, stacking_type=False))
            chart_id_ext_temp = EkogridChart.search(domain)
            if not chart_id_ext_temp:
                chart_id_ext_temp = EkogridChart.create(base_chart_attributes)
                [chart_id_ext_temp.add_serie_with_tasks_default([task.id]) for task in sensor_ext_temp]

    def pv_create_default_charts_inverter(self, base_domain, base_chart_attributes):
        """pv_create_default_charts_inverter method."""
        self.ensure_one()
        EkogridChart = self.env['ekogrid.chart']
        inv_int_temp = self.get_tasks('Inverter', 'Internal Temperature')
        sensor_irradiation = self.get_tasks('Sensor', 'Irradiation')
        sensor_irradiance = self.get_tasks('Sensor', 'Irradiance')
        inv_power = self.get_tasks('Inverter', 'AC Power')
        base_chart_attributes.update(dict(subtitle='Inverter', type='highstock'))
        base_domain_inv = base_domain + [('subtitle', '=', 'Inverter')]
        if inv_power or sensor_irradiance:
            ' # create AC Power charts'
            base_chart_attributes.update(dict(title='AC Power', aggregate='10 minute', time_frame='7', compute_deviation=False, stacking_type=False))
            chart_ids = EkogridChart.default_graphs_divider(inv_power, base_domain, base_chart_attributes)
            if sensor_irradiance:
                if chart_ids:
                    [chart_id.add_serie_with_tasks_default(sensor_irradiance.ids) for chart_id in chart_ids]
                else:
                    chart_id_sensor_irr = EkogridChart.create(base_chart_attributes)
                    chart_id_sensor_irr.add_serie_with_tasks_default(sensor_irradiance.ids)
            ' #create Total AC power'
            domain_total_inv = base_domain_inv + [('title', '=', 'Total AC Power'), ('task_ids', 'in', (inv_power + sensor_irradiance).ids)]
            base_chart_attributes.update(dict(title='Total AC Power', aggregate='10 minute', time_frame='today', compute_deviation=False, stacking_type='normal'))
            chart_id_inv_tot_power = EkogridChart.search(domain_total_inv)
            if not chart_id_inv_tot_power:
                chart_id_inv_tot_power = EkogridChart.create(base_chart_attributes)
                if inv_power:
                    [chart_id_inv_tot_power.add_serie_with_tasks_default([task.id], group='a', type='column') for task in inv_power]
                    chart_id_inv_tot_power.add_serie_with_tasks_default(inv_power.ids, group='b', name='Total AC Power', function='sum')
                if sensor_irradiance:
                    chart_id_inv_tot_power.add_serie_with_tasks_default(sensor_irradiance.ids, group='c')
        ' # create AC Output - Current charts'
        inv_ac_cur = self.get_tasks('Inverter', 'AC Current')
        inv_ac_cur_l1 = self.get_tasks('Inverter', 'AC Current L1')
        inv_ac_cur_l2 = self.get_tasks('Inverter', 'AC Current L2')
        inv_ac_cur_l3 = self.get_tasks('Inverter', 'AC Current L3')
        inv_ac_output = inv_ac_cur + inv_ac_cur_l1 + inv_ac_cur_l2 + inv_ac_cur_l3
        if inv_ac_output:
            domain_ac_curr = base_domain_inv + [('title', '=', 'AC Output - Current'), ('task_ids', 'in', inv_ac_output.ids)]
            base_chart_attributes.update(dict(title='AC Output - Current', aggregate='30 minute', time_frame='today', compute_deviation=True, stacking_type=False))
            chart_id_inv_ac_cur = EkogridChart.search(domain_ac_curr)
            if not chart_id_inv_ac_cur:
                chart_id_inv_ac_cur = EkogridChart.create(base_chart_attributes)
                [chart_id_inv_ac_cur.add_serie_with_tasks_default([task.id]) for task in inv_ac_output]
        ' #create AC Output - Voltage and Frequency charts'
        inv_ac_fre = self.get_tasks('Inverter', 'AC Frequency')
        inv_ac_vol = self.get_tasks('Inverter', 'AC Voltage')
        inv_ac_vol_l1 = self.get_tasks('Inverter', 'AC Voltage L1')
        inv_ac_vol_l2 = self.get_tasks('Inverter', 'AC Voltage L2')
        inv_ac_vol_l3 = self.get_tasks('Inverter', 'AC Voltage L3')
        inv_vol_l12 = self.get_tasks('Inverter', 'Voltage L1-L2')
        inv_vol_l23 = self.get_tasks('Inverter', 'Voltage L2-L3')
        inv_vol_l31 = self.get_tasks('Inverter', 'Voltage L3-L1')
        inv_ac_fre_vol = inv_ac_fre + inv_ac_vol + inv_ac_vol_l1 + inv_ac_vol_l2 + inv_ac_vol_l3 + inv_vol_l12 + inv_vol_l23 + inv_vol_l31
        if inv_ac_fre_vol:
            base_chart_attributes.update(dict(title='AC Output - Voltage and Frequency', aggregate='30 minute', time_frame='today', compute_deviation=False, stacking_type=False))
            EkogridChart.default_graphs_divider(inv_ac_fre_vol, base_domain, base_chart_attributes)
        ' # create DC Input charts '
        inv_dc_cur = self.get_tasks('Inverter', 'DC Current')
        inv_dc_vol = self.get_tasks('Inverter', 'DC Voltage')
        inv_dc_input = inv_int_temp + inv_dc_cur + inv_dc_vol
        if inv_dc_input:
            base_chart_attributes.update(dict(title='DC Input', aggregate='10 minute', time_frame='today', compute_deviation=False, stacking_type=False))
            EkogridChart.default_graphs_divider(inv_dc_input, base_domain, base_chart_attributes)
        ' # create AC PR charts '
        inv_pr = self.get_tasks('Inverter', 'AC PR')
        if inv_pr:
            domain_inv_pr = base_domain_inv + [('title', '=', 'AC PR'), ('task_ids', 'in', inv_pr.ids)]
            base_chart_attributes.update(dict(title='AC PR', aggregate='day', time_frame='31', compute_deviation=False, stacking_type=False))
            chart_id_inv_ac_pr = EkogridChart.search(domain_inv_pr)
            if not chart_id_inv_ac_pr:
                chart_id_inv_ac_pr = EkogridChart.create(base_chart_attributes)
                [chart_id_inv_ac_pr.add_serie_with_tasks_default([task.id]) for task in inv_pr]
        ' #create AC Energy (Inverter) charts'
        inv_ac_energy = self.get_tasks('Inverter', 'AC Energy Partial')
        if inv_ac_energy or sensor_irradiation:
            domain = base_domain_inv + [('task_ids', 'in', (inv_ac_energy + sensor_irradiation).ids)]
            domain_ac_daily = domain + [('title', '=', 'AC Energy Daily')]
            base_chart_attributes.update(dict(title='AC Energy Daily', aggregate='hour', time_frame='today', compute_deviation=False, stacking_type='normal'))
            chart_id_inv_ac_energy_day = EkogridChart.search(domain_ac_daily)
            if not chart_id_inv_ac_energy_day:
                chart_id_inv_ac_energy_day = EkogridChart.create(base_chart_attributes)
                [chart_id_inv_ac_energy_day.add_serie_with_tasks_default([task.id], group='a', type='column', function='sum', function_many='sum') for task in inv_ac_energy]
                chart_id_inv_ac_energy_day.add_serie_with_tasks_default(sensor_irradiation.ids, group='b')
            domain_ac_monthly = domain + [('title', '=', 'AC Energy Monthly')]
            base_chart_attributes.update(dict(title='AC Energy Monthly', aggregate='day', time_frame='31', compute_deviation=False, stacking_type=False))
            chart_id_inv_ac_energy_mon = EkogridChart.search(domain_ac_monthly)
            if not chart_id_inv_ac_energy_mon:
                chart_id_inv_ac_energy_mon = EkogridChart.create(base_chart_attributes)
                [chart_id_inv_ac_energy_mon.add_serie_with_tasks_default([task.id]) for task in inv_ac_energy]
                if sensor_irradiation:
                    chart_id_inv_ac_energy_mon.add_serie_with_tasks_default(sensor_irradiation.ids)

    def pv_create_default_stringBox_charts_fn(self, base_domain, base_chart_attributes):
        """pv_create_default_stringBox_charts_fn method."""
        self.ensure_one()
        EkogridChart = self.env['ekogrid.chart']
        sbx_cur = self.get_tasks('Stringbox', 'DC Current')
        sbx_pr = self.get_tasks('Stringbox', 'PR DC Current')
        sensor_mod_temp = self.get_tasks('Sensor', 'Module Temperature')
        base_domain = base_domain + [('subtitle', '=', 'StringBox')]
        base_chart_attributes.update(dict(subtitle='StringBox', time_frame='today', compute_deviation=False, stacking_type=False))
        ' # create DC Currents charts '
        if sbx_cur:
            base_chart_attributes.update(dict(title='DC Current', aggregate='10 minute'))
            EkogridChart.default_graphs_divider(sbx_cur, base_domain, base_chart_attributes, graph_types=True, series_attributes=dict())
        ' # create DC PR charts '
        if sbx_pr or sensor_mod_temp:
            base_chart_attributes.update(dict(title='DC PR', aggregate='hour'))
            chart_ids = EkogridChart.default_graphs_divider(sbx_pr, base_domain, base_chart_attributes, series_attributes=dict(type='column'))
            if sensor_mod_temp:
                if chart_ids:
                    [chart_id.add_serie_with_tasks_default(sensor_mod_temp.ids) for chart_id in chart_ids]
                else:
                    base_chart_attributes.update(dict(title='DC PR', aggregate='hour'))
                    chart_id_sbx_pr = EkogridChart.create(base_chart_attributes)
                    chart_id_sbx_pr.add_serie_with_tasks_default(sensor_mod_temp.ids)

    def photovoltaic_create_default_charts_fn(self):
        """photovoltaic_create_default_charts_fn method."""
        self.ensure_one()
        base_domain = [('plant_id', '=', self.id), ('chart_class', '=', 'base')]
        base_chart_attributes = dict(plant_ids=[(6, 0, [self.id])], chart_class='base')
        self.pv_create_default_charts_data_loggers(base_domain, base_chart_attributes)
        self.pv_create_default_charts_pv_production(base_domain, base_chart_attributes)
        self.pv_create_default_charts_sensor(base_domain, base_chart_attributes)
        self.pv_create_default_charts_inverter(base_domain, base_chart_attributes)
        self.pv_create_default_stringBox_charts_fn(base_domain, base_chart_attributes)