import pandas as pd
import numpy as np
from tqdm import trange
from clim_helpers import vvd_apply_value_flag
import glob
from os.path import basename, join


def vvd_gradient_check(df, grad_df, grad_variable, verbose=False):
    # Value vs depth gradient check
    # Check for gradients, inversions and zero sensitivity
    # df: value vs depth dataframe
    # grad_df: dataframe from WOA18 containing maximum gradient, inversion,
    #          and zero sensitivity index values to check vvd data against

    df['Gradient_check_flag'] = np.zeros(len(df), dtype=int)

    prof_start_ind = np.unique(df.Profile_number, return_index=True)[1]

    # Iterate through all of the profiles
    for i in trange(len(prof_start_ind)):  # len(prof_start_ind) 20
        # print(prof_start_ind[i])

        # Set profile end index
        if i == len(prof_start_ind) - 1:
            end_ind = len(df)
        else:
            # Pandas indexing is inclusive so need the -1
            end_ind = prof_start_ind[i + 1]

        # Get profile data; np.arange not inclusive of end which we want here
        indices = np.arange(prof_start_ind[i], end_ind)
        depths = df.loc[indices, 'Depth_m']
        values = df.loc[indices, 'Value']

        if verbose:
            print('Got values')

        # Try to speed up computations by skipping profiles with only 1 measurement
        if len(depths) <= 1:
            continue
        else:
            # gradients = np.zeros(len(depths), dtype=float)
            # for j in range(len(depths) - 1):
            # gradients[i] = (values[i + 1] - values[i]) / (depths[i + 1] - depths[i])

            # Use numpy built-in gradient method (uses 2nd order central differences)
            # Need fix for divide by zero
            gradients = np.gradient(values, depths)

            # Find the rate of change of gradient
            d_gradients = np.diff(gradients)

            # Create flags accordingly
            # If depth <= 400m and gradient < -max, apply one set of criteria
            # If depth > 400m and gradient < -max, apply other set of criteria...
            subsetter_MGV_lt_400 = np.where(
                (depths <= 400) & (gradients < -grad_df.loc[grad_variable, 'MGV_Z_lt_400m']))[0]
            subsetter_MGV_gt_400 = np.where(
                (depths > 400) & (gradients < -grad_df.loc[grad_variable, 'MGV_Z_gt_400m']))[0]
            subsetter_MIV_lt_400 = np.where(
                (depths <= 400) & (gradients > grad_df.loc[grad_variable, 'MIV_Z_lt_400m']))[0]
            subsetter_MIV_gt_400 = np.where(
                (depths > 400) & (gradients > grad_df.loc[grad_variable, 'MIV_Z_gt_400m']))[0]

            if verbose:
                print('Created MGV/MIV subsetters')

            # Zero sensitivity check
            # Only flag observations with Value = 0
            # If there are zero-as-missing-values at the very surface, then
            # the ZSI check wouldn't find them because it needs the gradient
            subsetter_ZSI_lt_400 = np.where(
                (depths[1:] <= 400) &
                (d_gradients < -grad_df.loc[
                    grad_variable, 'MGV_Z_lt_400m'] * grad_df.loc[grad_variable, 'ZSI']) &
                (values[1:] == 0.))[0]
            subsetter_ZSI_gt_400 = np.where(
                (depths[1:] > 400) &
                (d_gradients < -grad_df.loc[
                    grad_variable, 'MGV_Z_gt_400m'] * grad_df.loc[grad_variable, 'ZSI']) &
                (values[1:] == 0.))[0]

            if verbose:
                print('Created ZSI subsetters')

            # Flag the observations that failed the checks
            # "indices" span prof_start_ind[i] to the end of the profile
            df.loc[indices[np.union1d(subsetter_MGV_lt_400, subsetter_MGV_gt_400)],
                   'Gradient_check_flag'] = 1
            df.loc[indices[np.union1d(subsetter_MIV_lt_400, subsetter_MIV_gt_400)],
                   'Gradient_check_flag'] = 2

            # Flag = 3 for ZSI check failed
            # Flag = 4, for ZSI check and gradient check failed
            # Flag = 5 for ZSI check and inversion check failed
            df.loc[indices[np.union1d(subsetter_ZSI_lt_400, subsetter_ZSI_gt_400)],
                   'Gradient_check_flag'] += 3

    return df


# ------------------------STEP 3: Gradient checks--------------------------

# Now do gradient checks: flag=1 if check failed; flag=0 if check passed

# # Windows paths
# df_dir = 'C:\\Users\\HourstonH\\Documents\\NEP_climatology\\data\\' \
#          'value_vs_depth\\8_range_check\\'
# grad_file = 'C:\\Users\\HourstonH\\Documents\\NEP_climatology\\literature\\' \
#             'WOA docs\\wod18_users_manual_tables\\wod18_max_gradient_inversion.csv'
# df_outdir = 'C:\\Users\\HourstonH\\Documents\\NEP_climatology\\data\\' \
#                 'value_vs_depth\\9_gradient_check\\'

# Linux paths
df_dir = '/home/hourstonh/Documents/climatology/data/value_vs_depth/8_range_check/'
grad_file = '/home/hourstonh/Documents/climatology/literature/WOA docs/' \
            'wod18_users_manual_tables/wod18_max_gradient_inversion.csv'
df_outdir = '/home/hourstonh/Documents/climatology/data/value_vs_depth/9_gradient_check/'

# Read in table of WOD18 maximum gradients and inversions
df_grad = pd.read_csv(grad_file, index_col='Variable')

# for var, grad_var in zip(['Temp', 'Sal'], ['Temperature', 'Salinity']):
# for var, grad_var in zip(['Temp'], ['Temperature']):
# for var, grad_var in zip(['Temp', 'Sal'], ['Temperature', 'Salinity']):
for var, grad_var in zip(['Sal'], ['Salinity']):
    print(var, grad_var)
    # df_file = 'Oxy_1991_2020_value_vs_depth_rng_check_done.csv'
    # df_file = 'WOD_PFL_Oxy_1991_2020_value_vs_depth_rng_check_done.csv'
    vvd_files = glob.glob(df_dir + '*{}*rng_check_done.csv'.format(var))
    print(len(vvd_files))

    for df_file in vvd_files:
        print(basename(df_file))
        df_outname = df_outdir + basename(df_file).replace('rng_check_done', 'grad_check')
        print(df_outname)

        df_in = pd.read_csv(df_file)

        # Run gradient check
        df_out = vvd_gradient_check(df_in, df_grad, grad_var)

        print('Done gradient check')

        # Print summary statistics
        print(len(df_out.loc[df_out.Gradient_check_flag == 1, 'Gradient_check_flag']))  # gradient
        print(len(df_out.loc[df_out.Gradient_check_flag == 2, 'Gradient_check_flag']))  # inversion
        print(len(df_out.loc[df_out.Gradient_check_flag == 3, 'Gradient_check_flag']))  # ZSI
        print(len(df_out.loc[df_out.Gradient_check_flag == 4, 'Gradient_check_flag']))  # ZSI and gradient
        print(len(df_out.loc[df_out.Gradient_check_flag == 5, 'Gradient_check_flag']))  # ZSI and inversion

        df_outname = join(df_outdir, basename(df_file).replace('rng_check_done', 'grad_check'))
        print(df_outname)

        df_out.to_csv(df_outname, index=False)

        df_out2 = vvd_apply_value_flag(df_out, 'Gradient_check_flag')

        df_out2_name = df_outname.replace('grad_check', 'grad_check_done')
        print(df_out2_name)
        print()
        df_out2.to_csv(df_out2_name, index=False)
