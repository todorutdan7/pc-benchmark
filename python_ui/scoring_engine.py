import math
from config import REFERENCE_SYSTEM

class ScoringEngine:
    def __init__(self):
        self.results_cache = {}
        self.iteration_scores = {
            'cpu': [],
            'ram': [],
            'storage': [],
            'gpu': []
        }

    def clear_component_history(self, component):
        self.iteration_scores[component] = []
        if component in self.results_cache:
            self.results_cache[component] = []

    def update_result(self, test_type, data, iteration=None):
        if test_type in data:
            test_data = data[test_type]
        else:
            test_data = data
            
        if iteration is not None:
            if test_type not in self.results_cache:
                self.results_cache[test_type] = []
            self.results_cache[test_type].append(test_data)
            
            score = self._calculate_component_score(test_type, test_data)
            self.iteration_scores[test_type].append(score)
        else:

            self.results_cache[test_type] = [test_data]
            score = self._calculate_component_score(test_type, test_data)
            self.iteration_scores[test_type] = [score]

    def _calculate_component_score(self, component, data):

        ratios = []
        
        def safe_extract(extraction_logic):
            try:
                val = extraction_logic(data)
                if val is not None and isinstance(val, (int, float)) and val > 0:
                    return val
            except (KeyError, TypeError, ZeroDivisionError, IndexError, AttributeError):
                pass
            return None

        def get_bw(d_subset):
            return d_subset.get('read_bandwidth_gbs', 0)

        if "error" in data:
            return 0

        if component == 'cpu':

            t_pi_s = safe_extract(lambda d: d['pi_single_thread']['time_seconds'])
            if t_pi_s: ratios.append(REFERENCE_SYSTEM['cpu_pi_single_time_s'] / t_pi_s)

            t_pi_m = safe_extract(lambda d: d['pi_multi_thread']['time_seconds'])
            if t_pi_m: ratios.append(REFERENCE_SYSTEM['cpu_pi_multi_time_s'] / t_pi_m)

            t_mat_s = safe_extract(lambda d: d['matrix_single_thread']['time_seconds'])
            if t_mat_s: ratios.append(REFERENCE_SYSTEM['cpu_matrix_single_time_s'] / t_mat_s)

            t_mat_m = safe_extract(lambda d: d['matrix_multi_thread']['time_seconds'])
            if t_mat_m: ratios.append(REFERENCE_SYSTEM['cpu_matrix_multi_time_s'] / t_mat_m)

            t_int = safe_extract(lambda d: d['integer_hashing_single']['time_seconds'])
            if t_int: ratios.append(REFERENCE_SYSTEM['cpu_int_time_s'] / t_int)

            t_float = safe_extract(lambda d: d['float_math_single']['time_seconds'])
            if t_float: ratios.append(REFERENCE_SYSTEM['cpu_float_time_s'] / t_float)

        elif component == 'ram':

            bw_l1 = safe_extract(lambda d: get_bw(d['l1_cache']))
            if bw_l1: ratios.append(bw_l1 / REFERENCE_SYSTEM['ram_l1_bw'])

            bw_l2 = safe_extract(lambda d: get_bw(d['l2_cache']))
            if bw_l2: ratios.append(bw_l2 / REFERENCE_SYSTEM['ram_l2_bw'])

            bw_l3 = safe_extract(lambda d: get_bw(d['l3_cache']))
            if bw_l3: ratios.append(bw_l3 / REFERENCE_SYSTEM['ram_l3_bw'])

            bw_main = safe_extract(lambda d: get_bw(d['main_memory']))
            if bw_main: ratios.append(bw_main / REFERENCE_SYSTEM['ram_main_bw'])
            
            lat = safe_extract(lambda d: d['ram_latency']['avg_latency_ns'])
            if lat: ratios.append(REFERENCE_SYSTEM['ram_latency_ns'] / lat)

        elif component == 'storage':

            seq_r_iops = safe_extract(lambda d: d['sequential_read']['iops'])
            if seq_r_iops: ratios.append(seq_r_iops / REFERENCE_SYSTEM['disk_seq_read_iops'])

            seq_w_iops = safe_extract(lambda d: d['sequential_write']['iops'])
            if seq_w_iops: ratios.append(seq_w_iops / REFERENCE_SYSTEM['disk_seq_write_iops'])

            rnd_r = safe_extract(lambda d: d['random_read_iops']['iops'])
            if rnd_r: ratios.append(rnd_r / REFERENCE_SYSTEM['disk_rand_read_iops'])

            rnd_w = safe_extract(lambda d: d['random_write_iops']['iops'])
            if rnd_w: ratios.append(rnd_w / REFERENCE_SYSTEM['disk_rand_write_iops'])

        elif component == 'gpu':
            gflops = safe_extract(lambda d: d['mandelbrot']['gflops'])
            if gflops:
                ratios.append(gflops / REFERENCE_SYSTEM['gpu_gflops'])
    
            fps = safe_extract(lambda d: d['fps_test']['fps'])
            if fps:
                ratios.append(fps / REFERENCE_SYSTEM['gpu_fps'])

            if not ratios:
                return 0

        product = 1.0
        for r in ratios:
            product *= r
        
        geo_mean = product ** (1.0 / len(ratios))
        
        return int(geo_mean * 1000)

    def get_component_score(self, component):

        scores = self.iteration_scores.get(component, [])
        if not scores: return 0
        return int(sum(scores) / len(scores))

    def get_component_scores(self):

        return {
            'cpu': self.get_component_score('cpu'),
            'ram': self.get_component_score('ram'),
            'storage': self.get_component_score('storage'),
            'gpu': self.get_component_score('gpu')
        }

    def get_iteration_scores(self, component):
        return self.iteration_scores.get(component, [])

    def calculate_total_score(self):

        component_scores = self.get_component_scores()
        valid_scores = [s for s in component_scores.values() if s > 0]
        
        if not valid_scores:
            return 0, component_scores

        product = 1.0
        for score in valid_scores:
            product *= score
        
        geo_mean = product ** (1.0 / len(valid_scores))
        return int(geo_mean), component_scores